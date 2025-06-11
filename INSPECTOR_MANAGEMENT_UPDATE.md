# Inspector Management Security Update

## Overview
This update implements comprehensive role-based access control for inspector management as requested:

1. **Only superadmin** can assign/remove inspectors
2. **Only admin users (role_id=2)** can be assigned as inspectors 
3. **Admins can't assign themselves** as inspectors
4. **All superadmins are default inspectors** for all locations
5. **Admins only see locations** where they are assigned as inspectors

## Changes Made

### Backend Changes

#### 1. Location Service (`backend/app/services/location_service.py`)
- **Updated `list_locations` method**: Now filters locations based on user role
  - Admins only see locations where they are assigned as inspectors
  - Superadmins see all locations
- **Enhanced `assign_inspector` method**: 
  - Only superadmin (role_id=1) can assign inspectors
  - Only admin users (role_id=2) can be assigned as inspectors
  - Admins can't assign themselves as inspectors
- **Enhanced `unassign_inspector` method**: Only superadmin can remove inspectors

#### 2. Location Repository (`backend/app/domain/repositories/location_repository.py`)
- **Added `unassign_inspector` method**: Alias for consistency with service layer
- **Existing `get_locations_for_inspector` method**: Used to filter locations for admin users

#### 3. Location Router (`backend/app/api/v1/routers/location_router.py`)
- **Updated `_list_locations` endpoint**: Now passes current_user to service
- **Updated inspector management endpoints**: Only allow superadmin access
  - `POST /{location_id}/inspectors/{user_id}` - Superadmin only
  - `DELETE /{location_id}/inspectors/{user_id}` - Superadmin only

### Frontend Changes

#### 1. Location Inspectors Page (`frontend/src/pages/LocationInspectorsPage.tsx`)
- **Added role-based access control**: 
  - Only superadmin can see assign/remove controls
  - Admin users see "Access Denied" message with view-only inspector list
- **Enhanced user filtering**: Only show admin users (role_id=2) in assignment dropdown
- **Added proper imports**: AuthContext and RoleID constants

#### 2. Admin Locations Page (`frontend/src/pages/AdminLocationsPage.tsx`)
- **Updated inspector management button**: Only visible for superadmin users
- **Fixed TypeScript issues**: Proper handling of optional city_id field

### Database Changes

#### 1. Location Status Enum Extension (`db_schema/migrations/v6_add_location_status_values.sql`)
- **Added new enum values**: 'old' and 'new' to location_status type
- **Migration script**: `apply_migration.sql` includes both city_id nullable fix and enum updates

#### 2. Migration Script (`run_migration.py`)
- **Created Python script**: For easy database migration application
- **Verification included**: Checks that changes were applied correctly

## Security Features Implemented

### 1. Role-Based Access Control
- **Superadmin (role_id=1)**: 
  - Can assign/remove any inspector
  - Can see all locations
  - Can manage all inspector assignments
- **Admin (role_id=2)**:
  - Can only see locations they are assigned to as inspectors
  - Cannot assign/remove inspectors
  - Can only be assigned as inspectors (not other roles)

### 2. Business Logic Validations
- **Inspector assignment validation**: Only admin users can be assigned as inspectors
- **Self-assignment prevention**: Admins cannot assign themselves
- **User existence check**: Validates inspector user exists before assignment
- **Role verification**: Ensures only valid admin users are assigned

### 3. UI/UX Security
- **Conditional UI rendering**: Inspector management controls only shown to superadmin
- **Access denied messages**: Clear feedback when users lack permissions
- **View-only mode**: Non-superadmin users can still view current inspectors

## API Endpoints Security

### Protected Endpoints (Superadmin Only)
- `POST /api/v1/locations/{location_id}/inspectors/{user_id}` - Assign inspector
- `DELETE /api/v1/locations/{location_id}/inspectors/{user_id}` - Remove inspector

### Filtered Endpoints (Role-Based Results)
- `GET /api/v1/locations` - Returns filtered results based on user role

## How to Apply

### 1. Database Migration
```bash
# Option 1: Use Python script
python run_migration.py

# Option 2: Apply SQL directly
psql -h localhost -U postgre -d platform_db -f apply_migration.sql
```

### 2. Restart Backend
The backend changes require a restart to take effect.

### 3. Frontend
The frontend changes are automatically applied on next build/refresh.

## Verification Steps

1. **Database**: Verify enum values include 'old' and 'new'
2. **Superadmin Access**: Confirm superadmin can assign/remove inspectors
3. **Admin Restrictions**: Verify admin users cannot access inspector management
4. **Location Filtering**: Confirm admin users only see assigned locations
5. **Assignment Validation**: Test that only admin users can be assigned as inspectors

## Notes

- **Backward Compatibility**: Existing data is preserved
- **Graceful Degradation**: Non-superadmin users get clear access denied messages
- **Error Handling**: Proper error messages for invalid operations
- **Type Safety**: All TypeScript issues resolved with proper type handling 