"""Assets API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.asset import Asset, AssetType, AssetStatus
from app.models.project import Project
from app.schemas.asset import AssetCreate, AssetUpdate, AssetRead, AssetList, AssetUploadInit, AssetUploadComplete
import uuid

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create an asset record"""
    await _verify_project_access(str(asset_data.project_id), user_id, db)

    asset = Asset(**asset_data.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("/{project_id}", response_model=AssetList)
async def list_assets(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    asset_type: AssetType | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    status: AssetStatus | None = None,
):
    """List assets for a project with filters"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    query = select(Asset).where(Asset.project_id == project_uuid)

    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
    if episode_id:
        query = query.where(Asset.episode_id == uuid.UUID(episode_id))
    if scene_id:
        query = query.where(Asset.scene_id == uuid.UUID(scene_id))
    if status:
        query = query.where(Asset.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(Asset.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    assets = result.scalars().all()

    return AssetList(
        items=assets,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{project_id}/{asset_id}", response_model=AssetRead)
async def get_asset(
    project_id: str,
    asset_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific asset"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    asset_uuid = uuid.UUID(asset_id)

    result = await db.execute(
        select(Asset).where(Asset.id == asset_uuid, Asset.project_id == project_uuid)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{project_id}/{asset_id}", response_model=AssetRead)
async def update_asset(
    project_id: str,
    asset_id: str,
    asset_data: AssetUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update an asset"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    asset_uuid = uuid.UUID(asset_id)

    result = await db.execute(
        select(Asset).where(Asset.id == asset_uuid, Asset.project_id == project_uuid)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    update_data = asset_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)

    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/{project_id}/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    project_id: str,
    asset_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete an asset"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    asset_uuid = uuid.UUID(asset_id)

    result = await db.execute(
        select(Asset).where(Asset.id == asset_uuid, Asset.project_id == project_uuid)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await db.delete(asset)
    await db.commit()


@router.post("/upload/init", response_model=dict)
async def init_upload(
    upload_data: AssetUploadInit,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Initialize a file upload (returns presigned URL for S3 or local path)"""
    await _verify_project_access(str(upload_data.project_id), user_id, db)

    # For MVP, return a local upload path
    # In production, generate S3 presigned URL
    import uuid
    upload_id = str(uuid.uuid4())
    file_extension = upload_data.file_name.split(".")[-1] if "." in upload_data.file_name else "bin"
    file_path = f"uploads/{upload_data.project_id}/{upload_id}.{file_extension}"

    # Create asset record with pending status
    asset = Asset(
        project_id=upload_data.project_id,
        episode_id=upload_data.episode_id,
        scene_id=upload_data.scene_id,
        asset_type=upload_data.asset_type,
        file_name=upload_data.file_name,
        file_path=file_path,
        file_size=upload_data.file_size,
        mime_type=upload_data.mime_type,
        status=AssetStatus.UPLOADING,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    return {
        "upload_id": str(asset.id),
        "file_path": file_path,
        "upload_url": f"/api/assets/upload/{asset.id}",  # Local upload endpoint
    }


@router.post("/upload/{asset_id}", response_model=AssetRead)
async def complete_upload(
    asset_id: str,
    upload_data: AssetUploadComplete,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Complete file upload"""
    asset_uuid = uuid.UUID(asset_id)
    result = await db.execute(select(Asset).where(Asset.id == asset_uuid))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Verify project access
    await _verify_project_access(str(asset.project_id), user_id, db)

    asset.file_path = upload_data.file_path
    asset.status = AssetStatus.READY
    await db.commit()
    await db.refresh(asset)
    return asset