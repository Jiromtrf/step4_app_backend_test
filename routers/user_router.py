from fastapi import APIRouter, Depends, HTTPException, Header, status, Security
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from db.models import UserMaster, StatusTable, Specialty, Orientation, TeamMember
from utils.security import verify_token
from jose import JWTError
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from sqlalchemy.orm import joinedload

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

        # 所属チームIDを取得する処理を追加
        member_record = db.query(TeamMember).filter(TeamMember.user_id == user_id).first()
        team_id = member_record.team_id if member_record else None

        return {
            "user_id": user.user_id,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "core_time": user.core_time,
            "specialties": [s.specialty for s in user.specialties],
            "orientations": [o.orientation for o in user.orientations],
            "team_id": team_id  # チームIDを返す
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
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = db.query(UserMaster).filter(UserMaster.user_id == user_id).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        status_rec = db.query(StatusTable).filter(StatusTable.user_id == user_id).first()
        if status_rec is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User skills not found")

        skill_data = {
            "name": user.name,
            "biz": status_rec.biz,
            "design": status_rec.design,
            "tech": status_rec.tech
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
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        query = db.query(UserMaster).options(
            joinedload(UserMaster.specialties),     # specialtiesリレーションを事前ロード
            joinedload(UserMaster.orientations)     # orientationsリレーションを事前ロード
        )

        if filters.name:
            query = query.filter(UserMaster.name.ilike(f"%{filters.name}%"))

        if filters.specialties and len(filters.specialties) > 0:
            # specialtiesをフィルタに含める場合、JOIN済みならこのままfilter可能
            query = query.join(UserMaster.specialties).filter(Specialty.specialty.in_(filters.specialties))

        if filters.orientations and len(filters.orientations) > 0:
            query = query.join(UserMaster.orientations).filter(Orientation.orientation.in_(filters.orientations))

        users = query.all()

        result = []
        for u in users:
            specialties_list = [s.specialty for s in u.specialties] if u.specialties else []
            orientations_list = [o.orientation for o in u.orientations] if u.orientations else []
            
            result.append({
                "user_id": u.user_id,
                "name": u.name,
                "avatar_url": u.avatar_url,
                "specialties": specialties_list,
                "orientations": orientations_list,
                "core_time": u.core_time if u.core_time else ""
            })

        return {"data": result}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Unhandled error in search_users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")