from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session

from pydantic import BaseModel
from db.database import get_db
from db.models import UserMaster, StatusTable, TeamMember, Team
from utils.security import verify_token
from jose import JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime

router = APIRouter()

bearer_scheme = HTTPBearer()

class AddTeamMemberRequest(BaseModel):
    team_id: int
    role: str
    user_id: str

class CreateTeamRequest(BaseModel):
    name: str

@router.post("/api/team/add_member")
def add_team_member(
    request: AddTeamMemberRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = verify_token(credentials.credentials)
        # 認証されたユーザーの情報を使う場合は、ここでpayloadを利用

        new_member = TeamMember(
            team_id=request.team_id,
            role=request.role,
            user_id=request.user_id
        )
        db.add(new_member)
        db.commit()
        return {"message": "Team member added successfully."}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class RemoveTeamMemberRequest(BaseModel):
    team_id: int
    role: str

@router.delete("/api/team/remove_member")
def remove_team_member(
    request: RemoveTeamMemberRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = verify_token(credentials.credentials)
        # 認証されたユーザーの情報を使う場合は、ここでpayloadを利用

        member = db.query(TeamMember).filter(
            TeamMember.team_id == request.team_id,
            TeamMember.role == request.role
        ).first()

        if not member:
            raise HTTPException(status_code=404, detail="Member not found in this role.")

        db.delete(member)
        db.commit()
        return {"message": "Team member removed successfully."}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/team/{team_id}")
def get_team_info(
    team_id: int,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = verify_token(credentials.credentials)
        # 認証されたユーザーの情報を使う場合は、ここでpayloadを利用

        members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
        team_info = []
        for member in members:
            user = db.query(UserMaster).filter(UserMaster.user_id == member.user_id).first()
            status = db.query(StatusTable).filter(StatusTable.user_id == member.user_id).first()
            specialties = [s.specialty for s in user.specialties]
            orientations = [o.orientation for o in user.orientations]
            team_info.append({
                "role": member.role,
                "user_id": member.user_id,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "specialties": specialties,
                "orientations": orientations,
                "core_time": user.core_time,
                "biz": status.biz if status else None,
                "design": status.design if status else None,
                "tech": status.tech if status else None,
            })
        return team_info
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/api/team/create")
def create_team(
    request: CreateTeamRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # 新しいチームを作成
        new_team = Team(name=request.name)
        db.add(new_team)
        db.commit()
        db.refresh(new_team)

        # 作成者をPdMなど特定のロールで初期アサインするなどの対応も可能だが、ここでは空チームを返すだけ
        return {"team_id": new_team.id, "team_name": new_team.name}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))