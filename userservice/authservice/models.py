from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models import (
    Model, AutoField, EmailField, CharField,
    ForeignKey, CASCADE, BooleanField
)


class BaseModel(Model):
    """
    Abstract base model providing common fields for all models.
    """
    id = AutoField(primary_key=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, role=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')

        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, role=None, **extra_fields):
        if role is None:
            role, _ = Role.objects.get_or_create(role='admin')

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, role=role, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Model representing a user in the authentication service.
    """
    email = EmailField(unique=True, db_index=True)
    role = ForeignKey('Role', on_delete=CASCADE, related_name='users', null=True)
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email


class Role(BaseModel):
    """
    Model representing a role in the authentication service.
    """
    role = CharField(max_length=50, unique=True, db_index=True)

    class Meta:
        verbose_name_plural = 'roles'

    def __str__(self):
        return self.role
