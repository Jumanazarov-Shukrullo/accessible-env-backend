from datetime import timedelta
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from starlette.responses import RedirectResponse

from app.api.v1.dependencies import get_uow, require_roles
from app.core.auth import auth_manager
from app.core.config import settings
from app.core.constants import RoleID
from app.core.oauth import oauth
from app.core.security import security_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.permission_schema import PermissionCreate, PermissionResponse
from app.schemas.role_schema import RoleCreate, RoleResponse
from app.schemas.social_schema import FavouriteSchema
from app.schemas.user_schema import (
    InviteCreate,
    PaginatedMinimalUsers,
    PaginatedUsers,
    ProfilePictureResponse,
    Token,
    UserCreate,
    UserListResponse,
    UserResponse,
)
from app.services.permission_service import (
    can_invite_role,
    only_invite_admin_or_superadmin,
)
from app.services.role_service import RoleService
from app.services.social_service import SocialService
from app.services.user_service import UserService
from app.utils.email import EmailSender
from app.utils.logger import get_logger


router = APIRouter()
logger = get_logger("user_router")


class UserRouter:
    def __init__(self) -> None:
        self.router = router
        self.register_routes()

    def register_routes(self) -> None:
        self.router.add_api_route(
            "/",
            self.list_users,
            methods=["GET"],
            response_model=PaginatedUsers,
        )
        self.router.add_api_route(
            "/minimal",
            self.list_minimal_users,
            methods=["GET"],
            response_model=PaginatedMinimalUsers,
        )
        self.router.add_api_route(
            "/me", self.get_me, methods=["GET"], response_model=UserResponse
        )
        self.router.add_api_route(
            "/me", self.update_me, methods=["PUT"], response_model=UserResponse
        )
        self.router.add_api_route(
            "/me/profile-picture",
            self.upload_picture,
            methods=["PUT"],
            response_model=ProfilePictureResponse,
        )
        self.router.add_api_route(
            "/change-password", self.change_password, methods=["POST"]
        )
        self.router.add_api_route(
            "/forgot-password", self.forgot_password, methods=["POST"]
        )
        self.router.add_api_route(
            "/reset-password", self.reset_password, methods=["POST"]
        )
        self.router.add_api_route(
            "/register",
            self.register,
            methods=["POST"],
            response_model=UserResponse,
        )
        self.router.add_api_route(
            "/invite",
            self.invite_user,
            methods=["POST"],
            response_model=UserResponse,
            summary="[Superadmin only] Invite a new admin or superadmin",
        )
        self.router.add_api_route(
            "/token", self.login, methods=["POST"], response_model=Token
        )
        self.router.add_api_route(
            "/verify_email",
            self.verify_email,
            methods=["GET"],
            response_model=UserResponse,
        )
        self.router.add_api_route(
            "/google/login", self.google_login, methods=["GET"]
        )
        self.router.add_api_route(
            "/google/callback",
            self.google_callback,
            methods=["GET", "POST"],
            response_model=Token,
            operation_id="google_callback_oauth_get_post",
        )
        self.router.add_api_route(
            "/{user_id}/role",
            self.change_role,
            methods=["PUT"],
            response_model=UserResponse,
        )
        self.router.add_api_route(
            "/{user_id}/ban",
            self.ban_user,
            methods=["PUT"],
            response_model=UserResponse,
        )
        self.router.add_api_route(
            "/{user_id}/unban",
            self.unban_user,
            methods=["PUT"],
            response_model=UserResponse,
        )
        self.router.add_api_route(
            "/roles",
            self.create_role,
            methods=["POST"],
            response_model=RoleResponse,
        )
        self.router.add_api_route(
            "/permissions",
            self.create_permission,
            methods=["POST"],
            response_model=PermissionResponse,
        )
        self.router.add_api_route(
            "/roles/{role_id}/assign_permission/{permission_id}",
            self.assign_permission,
            methods=["POST"],
        )
        self.router.add_api_route(
            "/resend-verification", self.resend_verification, methods=["POST"]
        )
        self.router.add_api_route(
            "/favorites",
            self.get_favorites,
            methods=["GET"],
            response_model=List[FavouriteSchema.Out],
        )
        self.router.add_api_route(
            "/{user_id}",
            self.get_user_details,
            methods=["GET"],
            response_model=UserResponse,
            summary="[Admin] Get user details by ID",
        )

    async def register(
        self,
        user_in: UserCreate,
        background_tasks: BackgroundTasks,
        uow: UnitOfWork = Depends(get_uow),
    ) -> User:
        service = UserService(uow)
        user, verification_link = service.register_user(user_in)
        background_tasks.add_task(
            EmailSender.send_verification_email, user.email, verification_link
        )
        return user

    async def list_users(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(5, ge=1, le=100),
        role_id: Optional[int] = Query(None, description="Filter by role ID"),
        search: Optional[str] = Query(
            None, description="Search in username, email, first name, surname"
        ),
        _optimize: Optional[bool] = Query(
            None, description="Hint for backend optimization"
        ),
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(
            require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])
        ),
    ) -> PaginatedUsers:
        logger.info(
            f"Listing users [page={page}, page_size={page_size}, role_id={role_id}, search={search}, optimize={_optimize}]"
        )
        offset = (page - 1) * page_size
        service = UserService(uow)

        # Cache key for improved response caching
        # cache_key removed - was unused

        # Choose the appropriate query method based on filters
        if search:
            users_data, total = service.search_users(
                search, limit=page_size, offset=offset
            )
        elif role_id is not None:
            users_data, total = service.list_users_by_role(
                role_id, limit=page_size, offset=offset
            )
        else:
            users_data, total = service.get_users_paginated(page=page, size=page_size, search=search)

        # Construct full_name for each user if not already present
        processed_users = []
        for user in users_data:
            # Convert to dict for manipulation
            user_dict = (
                user.model_dump()
                if hasattr(user, "model_dump")
                else user.dict()
            )

            if "full_name" not in user_dict or not user_dict["full_name"]:
                middle = (
                    f" {user_dict.get('middle_name', '')} "
                    if user_dict.get("middle_name")
                    else " "
                )
                user_dict["full_name"] = (
                    f"{user_dict['first_name']}{middle}{user_dict['surname']}".replace(
                        "  ", " "
                    )
                )

            processed_users.append(UserListResponse(**user_dict))

        response = PaginatedUsers(users=processed_users, total=total)

        # Add optimization headers for front-end caching# Headers removed - was unused  # Cache for 5 minutes

        return response

    async def invite_user(
        self,
        payload: InviteCreate,
        background_tasks: BackgroundTasks,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(
            require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])
        ),
    ) -> UserCreate:

        only_invite_admin_or_superadmin(payload)
        can_invite_role(current_user, payload.role_id)

        service = UserService(uow)
        new_user, temp_password = service.create_user_with_role(
            user_in=payload, created_by=current_user
        )

        background_tasks.add_task(
            EmailSender.send_invitation_email,
            new_user.email,
            new_user.username,
            temp_password,
        )

        return new_user

    async def login(
        self,
        form_data: OAuth2PasswordRequestForm = Depends(),
        uow: UnitOfWork = Depends(get_uow),
    ) -> Token:
        service = UserService(uow)
        login_value = form_data.username
        if "@" in login_value:
            user = service.get_user_by_email(login_value)
        else:
            user = service.get_user_by_username(login_value)

        logger.info(f"LOGIN DEBUG - USER: {user}")
        if not user:
            logger.warning("LOGIN DEBUG - User not found")
        else:
            try:
                security_manager.verify_password(
                    form_data.password, user.password_hash
                )
            except AttributeError:
                logger.error(
                    "LOGIN DEBUG - security_manager missing on UserService"
                )
                raise
        if not user or not security_manager.verify_password(
            form_data.password, user.password_hash
        ):
            logger.error("LOGIN DEBUG - Invalid credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        access_token_expires = timedelta(
            minutes=settings.auth.access_token_expires
        )
        access_token = security_manager.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        logger.info(
            f"LOGIN DEBUG - Login successful for user: {user.username}"
        )
        token_obj = Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.auth.access_token_expires
            * 60,  # Convert minutes to seconds
        )
        logger.info(f"LOGIN DEBUG - Token object created: {token_obj}")
        logger.info(f"LOGIN DEBUG - Token dict: {token_obj.model_dump()}")
        return token_obj

    @staticmethod
    async def verify_email(
        token: str, uow: UnitOfWork = Depends(get_uow)
    ) -> User:
        service = UserService(uow)
        user = service.verify_email(token)
        return RedirectResponse(
            f"{settings.auth.frontend_base_url}/email-verified?username={user.username}"
        )

    async def resend_verification(
        self,
        user: User = Depends(auth_manager.get_current_user),
        uow: UnitOfWork = Depends(get_uow),
        background_tasks: BackgroundTasks = BackgroundTasks(),
    ) -> dict:
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified",
            )

        token = self._generate_verification_token(user)
        verification_link = self._get_verification_link(token)
        background_tasks.add_task(
            EmailSender.send_verification_email, user.email, verification_link
        )
        return {"message": "Verification email sent"}

    async def google_login(self, request: Request):
        """
        Redirect user to Google LoginPage
        """
        redirect_url = settings.auth.google_redirect_uri
        # redirect_uri must match the authorized redirect in google console
        return await oauth.google.authorize_redirect(request, redirect_url)

    async def google_callback(
        self, request: Request, uow: UnitOfWork = Depends(get_uow)
    ) -> Token:
        """
        Exchange the authorization code for tokens, get user info, upsert user in db
        then return local jwt
        """
        try:
            token = await oauth.google.authorize_access_token(request)
        except Exception:
            import traceback

            print("EXCEPTION", traceback.format_exc())
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google OAuth callback failed",
            )

        resp = await oauth.google.get("userinfo", token=token)
        user_info = resp.json()

        # Debug logging
        print(f"DEBUG: Google user info received: {user_info}")

        if not user_info.get("email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No email provided by Google",
            )

        service = UserService(uow)
        user = service.upsert_google_user(user_info)

        access_token = security_manager.create_access_token(
            data={"sub": user.username}
        )
        return RedirectResponse(
            f"{settings.auth.frontend_base_url}/oauth/callback?access_token={access_token}"
        )

    async def change_role(
        self,
        user_id: str,
        new_role: int = Query(
            ...,
            alias="new_role",
            description="Role ID to assign (1=Superadmin, 2=Admin, 3=User)",
        ),
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(
            require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])
        ),
    ) -> UserResponse:
        service = UserService(uow)
        updated_user = service.change_role(user_id, new_role, current_user)
        return updated_user

    async def ban_user(
        self,
        user_id: str,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(
            require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])
        ),
    ) -> UserResponse:
        service = UserService(uow)
        banned_user = service.ban_user(user_id, current_user)
        return banned_user

    async def unban_user(
        self,
        user_id: str,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(
            require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])
        ),
    ) -> UserResponse:
        service = UserService(uow)
        unbanned_user = service.unban_user(user_id)
        return unbanned_user

    async def create_role(
        self,
        role_in: RoleCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(require_roles([RoleID.SUPERADMIN.value])),
    ) -> RoleResponse:
        role_service = RoleService(uow)
        role = role_service.create_role(role_in)
        return role

    async def create_permission(
        self,
        permission_in: PermissionCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(require_roles([RoleID.SUPERADMIN.value])),
    ) -> PermissionResponse:
        role_service = RoleService(uow)
        permission = role_service.create_permission(permission_in)
        return permission

    async def assign_permission(
        self,
        role_id: int,
        permission_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(
            require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])
        ),
    ) -> dict:
        role_service = RoleService(uow)
        assignment = role_service.assign_permission_to_role(
            role_id, permission_id
        )
        return {
            "role_id": assignment.role_id,
            "permission_id": assignment.permission_id,
            "granted_at": assignment.granted_at,
        }

    async def get_me(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> UserResponse:
        user_service = UserService(uow)
        return user_service.get_user_with_profile(str(current_user.user_id))

    async def update_me(
        self,
        payload: dict,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> UserResponse:
        user_service = UserService(uow)
        return user_service.update_profile(current_user, payload)

    async def upload_picture(
        self,
        file: UploadFile = File(...),
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> ProfilePictureResponse:
        url = UserService(uow).update_profile_picture(current_user, file)
        return {"url": url}

    async def change_password(
        self,
        data: dict,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> dict:
        UserService(uow).change_password(
            current_user, data["old_password"], data["new_password"]
        )
        return {"message": "Password changed successfully"}

    async def forgot_password(
        self,
        body: dict,
        background_tasks: BackgroundTasks,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> dict:
        user_service = UserService(uow)
        user = user_service.get_user_by_email(body["email"])
        if user:
            token = user_service.generate_password_reset_token(user)
            link = f"{
                settings.auth.frontend_base_url}/reset-password?token={token}"
            background_tasks.add_task(
                EmailSender.send_password_reset_email, user.email, link
            )
        return {"message": "Password reset email sent"}

    async def reset_password(
        self,
        body: dict,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> dict:
        user_service = UserService(uow)
        user_service.reset_password(body["token"], body["new_password"])
        return {"message": "Password reset successfully"}

    async def list_minimal_users(
        self,
        role_id: Optional[int] = Query(None, description="Filter by role ID"),
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> PaginatedMinimalUsers:
        """Get a lightweight list of users suitable for dropdown menus and selection inputs"""
        service = UserService(uow)
        if role_id is not None:
            # For role-specific filtering, use more limited fields
            fields = [
                "user_id",
                "username",
                "first_name",
                "surname",
                "middle_name",
            ]
            users_data = service.repo.get_users_by_role(
                role_id, fields, limit=100
            )
            total = service.repo.count_by_role(role_id)
        else:
            # Very minimal fields for general listing
            fields = [
                "user_id",
                "username",
                "first_name",
                "surname",
                "middle_name",
            ]
            users_data = service.repo.get_specific_fields(fields, limit=100)
            total = service.repo.count()

        # Construct full_name from first_name and surname and convert user_id
        # to string
        users = []
        for user in users_data:
            full_name = f"{
                user['first_name']} {
                user.get(
                    'middle_name',
                    '')} {
                user['surname']}".strip().replace(
                    "  ",
                " ")
            users.append(
                {
                    "user_id": str(user["user_id"]),  # Convert UUID to string
                    "username": user["username"],
                    "full_name": full_name,
                }
            )

        return PaginatedMinimalUsers(users=users, total=total)

    async def get_favorites(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> List[FavouriteSchema.Out]:
        service = SocialService(uow)
        favorites = service.list_user_favs(current_user.user_id)
        return favorites

    async def get_user_details(
        self,
        user_id: str,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(
            require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])
        ),
    ) -> UserResponse:
        """Return full user information (including profile) for admin dashboard view."""
        service = UserService(uow)
        user = service.get_user_with_profile(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user


user_router_instance = UserRouter()
