from fastapi import APIRouter, Depends, HTTPException, Header, status,  Security
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from db.models import UserMaster, StatusTable, Specialty, Orientation
from utils.security import verify_token
from jose import JWTError
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging


router = APIRouter()
logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()

class UserFilter(BaseModel):
    name: Optional[str] = None
    specialties: Optional[List[str]] = None
    orientations: Optional[List[str]] = None

@router.get("/api/user/me")
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(UserMaster).filter(UserMaster.user_id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": user.user_id,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "core_time": user.core_time,
            "specialties": [s.specialty for s in user.specialties],
            "orientations": [o.orientation for o in user.orientations]
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/user/skills")
def get_user_skills(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
):
    try:
        # トークンを検証し、ペイロードを取得
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # ユーザー情報を取得
        user = db.query(UserMaster).filter(UserMaster.user_id == user_id).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # ステータステーブルからスキル情報を取得
        status = db.query(StatusTable).filter(StatusTable.user_id == user_id).first()
        if status is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User skills not found")

        # スキルデータを構築
        skill_data = {
            "name": user.name,
            "biz": status.biz,
            "design": status.design,
            "tech": status.tech
        }

        return skill_data
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception as e:
        logger.error(f"Unhandled error in get_user_skills: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.post("/api/user/search")
def search_users(
    filters: UserFilter,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
):
    try:
        # トークンを検証し、ペイロードを取得
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # 検索クエリの構築
        query = db.query(UserMaster)

        if filters.name:
            query = query.filter(UserMaster.name.ilike(f"%{filters.name}%"))

        if filters.specialties:
            query = query.join(UserMaster.specialties).filter(Specialty.specialty.in_(filters.specialties))

        if filters.orientations:
            query = query.join(UserMaster.orientations).filter(Orientation.orientation.in_(filters.orientations))

        users = query.all()

        result = []
        for user in users:
            specialties = [s.specialty for s in user.specialties]
            orientations = [o.orientation for o in user.orientations]
            result.append({
                "user_id": user.user_id,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "specialties": specialties,
                "orientations": orientations,
                "core_time": user.core_time
            })

        return {"data": result}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception as e:
        logger.error(f"Unhandled error in search_users: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
