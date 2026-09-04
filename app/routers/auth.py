from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import User
from app.schemas.schemas import UserCreate, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=201)
@limiter.limit("5/minute")
def signup(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """Rate-limited to 5 signups/minute per IP - slows automated account creation."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Rate-limited to 10 attempts/minute per IP - the main brute-force defense
    for password guessing, since there's no account lockout mechanism yet."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(data={"sub": user.id})
    return Token(access_token=token)
