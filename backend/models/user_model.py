from dataclasses import dataclass


VALID_ROLES = {"ADMIN", "RECRUITER", "CANDIDATE"}


@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str
    role: str
    company_name: str | None
    created_at: str

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            role=row["role"],
            company_name=row["company_name"],
            created_at=row["created_at"],
        )

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "company_name": self.company_name,
            "created_at": self.created_at,
        }
