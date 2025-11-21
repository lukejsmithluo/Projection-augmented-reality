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
    aspect_ratio: Optional[str] = Form(None),
    image_resolution: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
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

    # Determine provider (default remains OpenAI to keep existing tests stable)
    prov = (provider or "").strip().lower()
    if not prov:
        m = (model or "").strip().lower()
        if m.startswith("gemini") or m.startswith("imagen"):
            prov = "gemini"
        else:
            prov = "openai"

    # Allow providing API key via request to set env at runtime (optional)
    if api_key:
        if prov == "gemini":
            # Prefer GEMINI_API_KEY; client also accepts GOOGLE_API_KEY
            os.environ["GEMINI_API_KEY"] = api_key
        else:
            os.environ["OPENAI_API_KEY"] = api_key
    if api_org_id and prov == "openai":
        os.environ["OPENAI_ORG_ID"] = api_org_id

    # Validate API key presence (avoid external call when missing)
    if prov == "gemini":
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            return AIImageEditResponse(
                accepted=False,
                error_code="NO_API_KEY",
                error="GEMINI_API_KEY not configured",
            )
    else:
        if not os.getenv("OPENAI_API_KEY"):
            return AIImageEditResponse(
                accepted=False,
                error_code="NO_API_KEY",
                error="OPENAI_API_KEY not configured",
            )

    # Input validation per provider
    if prov == "openai":
        if size:
            allowed_sizes = {"256x256", "512x512", "1024x1024"}
            if size.lower() not in allowed_sizes:
                return AIImageEditResponse(
                    accepted=False,
                    error_code="BAD_SIZE",
                    error="Invalid size for gpt-image-1. Allowed: 256x256, 512x512, 1024x1024",
                )
    else:
        # Gemini inputs: aspect_ratio and optional image_resolution
        if aspect_ratio:
            allowed_ratios = {"1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"}
            if aspect_ratio not in allowed_ratios:
                return AIImageEditResponse(
                    accepted=False,
                    error_code="BAD_ASPECT_RATIO",
                    error="Invalid aspect_ratio. Allowed: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9",
                )
        if image_resolution:
            allowed_res = {"1K","2K","4K"}
            if image_resolution.upper() not in allowed_res:
                return AIImageEditResponse(
                    accepted=False,
                    error_code="BAD_IMAGE_RESOLUTION",
                    error="Invalid image_resolution. Allowed: 1K, 2K, 4K (uppercase K)",
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

    # Region policy check (hybrid): only allow official supported countries/territories (provider-aware)
    try:
        # Prefer provider-aware evaluation if available
        try:
            region = policy.evaluate(prov)
        except TypeError:
            # Backward compatibility: older evaluate() without args
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

    # 限制上传数量（按提供商与模型）
    m_lower = (model or "").strip().lower()
    max_images = 1 if prov == "openai" else 16
    if prov == "gemini":
        if m_lower.startswith("gemini-3-pro-image-preview"):
            max_images = 14  # 来自官方预览限制
        elif m_lower.startswith("gemini-2.5"):
            # Gemini 2.5 理论支持大量图片，考虑到令牌/大小与性能，后端默认温和限制
            max_images = 16
    else:
        # OpenAI gpt-image-1 走 Images Edit，仅支持单图
        max_images = 1

    if len(img_list) > max_images:
        return AIImageEditResponse(
            accepted=False,
            error_code="TOO_MANY_IMAGES",
            error=f"Too many images for provider={prov} model={(model or '').strip()}. Max is {max_images}.",
        )

    # 处理：保存所有上传图片（唯一命名），并以最后一张作为生成输入
    # OpenAI Images API 当前仅接受单图编辑；Gemini 路径亦保持单图输入（后续可扩展）
    last_out: Optional[str] = None
    try:
        # 先保存除最后一张外的所有上传文件
        if len(img_list) > 1:
            for up in img_list[:-1]:
                data_pre = await up.read()
                try:
                    mod.save_upload(upload_name=up.filename or "upload.png", content=data_pre)
                except Exception:
                    # 不中断主流程，保存失败不影响生成；错误由统一异常处理覆盖
                    pass

        # 最后一张作为有效输入进行生成（该调用内部也会保存到 uploads）
        target = img_list[-1]
        data = await target.read()
        last_out = mod.edit_image(
            prompt=prompt,
            upload_name=target.filename or "upload.png",
            content=data,
            size=size,
            model=model,
            aspect_ratio=aspect_ratio,
            image_resolution=image_resolution,
            provider=prov,
        )
    except Exception as e:
        msg = str(e)
        if prov == "openai" and "OPENAI_ORG_NOT_VERIFIED" in msg:
            return AIImageEditResponse(
                accepted=False,
                error_code="ORG_NOT_VERIFIED",
                error=(
                    "Organization not verified for gpt-image-1."
                    " Please verify at https://platform.openai.com/settings/organization/general"
                    " and wait up to ~15 minutes for access to propagate."
                ),
            )
        if prov == "gemini" and (
            "GEMINI_LIB_MISSING" in msg or "GEMINI_NO_IMAGE_DATA" in msg or "PIL_OR_GEMINI_TYPES_MISSING" in msg
        ):
            # Return a friendly message for common setup issues
            return AIImageEditResponse(
                accepted=False,
                error_code="GENERATION_FAILED",
                error=(
                    "Gemini image generation failed (missing library or no image output). "
                    "Ensure 'google-genai' and 'Pillow' are installed and your API key is valid."
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
