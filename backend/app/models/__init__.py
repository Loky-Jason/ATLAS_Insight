"""Import all models so SQLAlchemy registers them on Base.metadata."""

from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.course_proposal import CourseProposal
from app.models.favorite import Favorite
from app.models.gap_recommendation import GapRecommendation
from app.models.market_course import MarketCourse
from app.models.market_scan_run import MarketScanRun
from app.models.school_course import SchoolCourse
from app.models.school_registry import SchoolRegistry
from app.models.user import User

__all__ = [
    "User", "Course", "MarketCourse", "CourseProposal", "AuditLog", "Favorite",
    "SchoolRegistry", "SchoolCourse", "MarketScanRun", "GapRecommendation",
]
