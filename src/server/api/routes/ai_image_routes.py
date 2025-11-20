from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from ....common.registry import ModuleRegistry
from ....modules.ai_image_generation.module import AIImageGenerationModule
from ..deps import get_region_policy, get_registry
from ..schemas.ai_image import AIImageEditResponse

router = APIRouter(tags=["ai-image"])


@router.post("/edit", response_model=AIImageEditResponse)
async def edit_image(
    prompt: str = Form(...),
    size: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    image: Optional[UploadFile] = File(None),
    api_key: Optional[str] = Form(None),
    api_org_id: Optional[str] = Form(None),
    registry: ModuleRegistry = Depends(get_registry),
    policy=Depends(get_region_policy),
):
    """Edit the uploaded image using OpenAI with the given prompt.

    Accepts multipart/form-data: prompt (text), image (file), optional size.
    Returns saved output file path on success.
    """
    # Validate module
    mod = registry.get("ai_image_generation")
    if mod is None or not isinstance(mod, AIImageGenerationModule):
        return AIImageEditResponse(
            accepted=False,
            error_code="MODULE_NOT_REGISTERED",
            error="Module not registered",
        )

    # Allow providing API key via request to set env at runtime (optional)
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if api_org_id:
        os.environ["OPENAI_ORG_ID"] = api_org_id
    # Validate API key presence (avoid external call when missing)
    if not os.getenv("OPENAI_API_KEY"):
        return AIImageEditResponse(
            accepted=False,
            error_code="NO_API_KEY",
            error="OPENAI_API_KEY not configured",
        )

    # Collect images preserving order: earliest -> latest
    img_list: List[UploadFile] = []
    if images:
        img_list = list(images)
    elif image:
        img_list = [image]
    else:
        return AIImageEditResponse(
            accepted=False, error_code="NO_IMAGE", error="No image provided"
        )

    # Basic content-type check (optional)
    for img in img_list:
        if img.content_type and not img.content_type.startswith("image/"):
            return AIImageEditResponse(
                accepted=False,
                error_code="BAD_CONTENT_TYPE",
                error=f"Unsupported content type: {img.content_type}",
            )

    # Region policy check (hybrid): only allow official supported countries/territories
    try:
        region = policy.evaluate()
        if not region.allowed:
            return AIImageEditResponse(
                accepted=False,
                error_code="REGION_BLOCKED",
                error=(
                    f"Region not allowed: country={region.country_code or 'UNKNOWN'} "
                    f"subdivision={region.subdivision or '-'} reason={region.reason or ''}"
                ),
            )
    except Exception as e:
        # Any failure in region check results in conservative block
        return AIImageEditResponse(
            accepted=False,
            error_code="REGION_CHECK_FAILED",
            error=str(e),
        )

    # Process; if multiple provided, use the latest one as effective input
    # (OpenAI Images API currently accepts single image per edit call)
    last_out: Optional[str] = None
    try:
        # Choose the last image as the effective input to generate
        target = img_list[-1]
        data = await target.read()
        last_out = mod.edit_image(
            prompt=prompt,
            upload_name=target.filename or "upload.png",
            content=data,
            size=size,
            model=model,
        )
    except Exception as e:
        msg = str(e)
        if "OPENAI_ORG_NOT_VERIFIED" in msg:
            return AIImageEditResponse(
                accepted=False,
                error_code="ORG_NOT_VERIFIED",
                error=(
                    "Organization not verified for gpt-image-1."
                    " Please verify at https://platform.openai.com/settings/organization/general"
                    " and wait up to ~15 minutes for access to propagate."
                ),
            )
        return AIImageEditResponse(
            accepted=False, error_code="GENERATION_FAILED", error=str(e)
        )

    return AIImageEditResponse(accepted=True, output_file=last_out)


@router.get("/status")
def status(registry: ModuleRegistry = Depends(get_registry)):
    mod = registry.get("ai_image_generation")
    return {"module": "ai_image_generation", "status": mod.status() if mod else None}
