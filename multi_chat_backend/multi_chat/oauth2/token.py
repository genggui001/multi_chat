from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from multi_chat.models import ResponseCode, ResponseWrapper
from multi_chat.mongo.models import User
from multi_chat.mongo.user import (authenticate_user, create_access_token,
                                   get_password_hash)
from pydantic import BaseModel

from multi_chat import config


class Token(BaseModel):
    access_token: str
    token_type: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    register_code: str
    
class RegisterResponse(BaseModel):
    message: str

router = APIRouter()


@router.post("/token", response_model=ResponseWrapper[Token])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.oauth2.access_token_expire_minutes)
    access_token = create_access_token(
        username=user.username, expires_delta=access_token_expires
    )
    return ResponseWrapper(
        code=ResponseCode.success,
        result=Token(
            access_token=access_token,
            token_type="bearer"
        )
    )


@router.post("/register", response_model=ResponseWrapper[RegisterResponse])
async def register(data: RegisterRequest) -> ResponseWrapper[RegisterResponse]:

    if data.register_code not in {
        '32ju1',
        '56ka3',
        '77uq1',
        '9m21g',
        'ss1d5',
    }:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Register code is not available.",
        )

    user = await User.get(username=data.username)
    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Username is already registered.",
        )
    
    await User.new(
        username=data.username,
        hashed_password=get_password_hash(data.password)
    )
    return ResponseWrapper(
        code=ResponseCode.success,
        result=RegisterResponse(
            message="success"
        )
    )
