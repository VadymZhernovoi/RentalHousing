from .enums import Roles

def is_admin(user):     
    return user.is_authenticated and (user.is_superuser or getattr(user, "is_staff", False)
            or getattr(user, "role", "") == Roles.ADMIN)

def is_renter(user):    
    return user.is_authenticated and getattr(user, "role", "") == Roles.RENTER

def is_lessor(user):    
    return user.is_authenticated and getattr(user, "role", "") == Roles.LESSOR

def is_moderator(user): 
    return user.is_authenticated and getattr(user, "role", "") == Roles.MODERATOR

# def is_admin(u):
#     return u.is_authenticated and (u.is_superuser or getattr(u, "is_staff", False) or getattr(u, "role", "") == "admin")
#
# def is_moderator(u):
#     return u.is_authenticated and getattr(u, "role", "") == "moderator"
#
# def is_lessor(u):
#     return u.is_authenticated and getattr(u, "role", "") in ("lessor", "landlord")
#
# def is_renter(u):
#     return u.is_authenticated and getattr(u, "role", "") == "renter"