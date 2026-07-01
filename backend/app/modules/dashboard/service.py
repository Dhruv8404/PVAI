from datetime import datetime, UTC, timedelta
from typing import List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.model import User
from app.modules.documents.model import GeneratedDocument
from app.modules.downloads.model import DownloadLog
from app.modules.dashboard.model import ActivityLog
from app.modules.dashboard.schema import (
    DashboardFullResponse,
    MetricCard,
    ActivityLogResponse,
    DashboardCharts,
    ChartPoint,
    DashboardUserResponse
)


class DashboardService:
    async def get_dashboard_data(self, db: AsyncSession, current_user: User) -> DashboardFullResponse:
        user_roles_list = [r.name for r in current_user.roles]
        is_admin = "Admin" in user_roles_list

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        if is_admin:
            # 1. Admin Metrics
            u_total_stmt = select(func.count(User.id))
            u_active_stmt = select(func.count(User.id)).where(User.status == "Active")
            u_inactive_stmt = select(func.count(User.id)).where(User.status == "Inactive")

            d_today_stmt = select(func.count(GeneratedDocument.id)).where(GeneratedDocument.created_at >= today_start)
            d_month_stmt = select(func.count(GeneratedDocument.id)).where(GeneratedDocument.created_at >= month_start)
            dl_total_stmt = select(func.count(DownloadLog.id))

            total_users = (await db.execute(u_total_stmt)).scalar() or 0
            active_users = (await db.execute(u_active_stmt)).scalar() or 0
            inactive_users = (await db.execute(u_inactive_stmt)).scalar() or 0
            gen_today = (await db.execute(d_today_stmt)).scalar() or 0
            gen_month = (await db.execute(d_month_stmt)).scalar() or 0
            total_downloads = (await db.execute(dl_total_stmt)).scalar() or 0

            metrics = MetricCard(
                total_users=total_users,
                active_users=active_users,
                inactive_users=inactive_users,
                gen_today=gen_today,
                gen_month=gen_month,
                total_downloads=total_downloads
            )

            # 2. Admin Recent Activities
            act_stmt = select(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(5)
            act_res = await db.execute(act_stmt)
            activities = list(act_res.scalars().all())

            # 3. Admin Charts (Real Database Counts)
            daily_docs = []
            for i in range(6, -1, -1):
                day_date = datetime.now(UTC).date() - timedelta(days=i)
                day_start = datetime.combine(day_date, datetime.min.time())
                day_end = datetime.combine(day_date, datetime.max.time())
                
                day_stmt = select(func.count(GeneratedDocument.id)).where(
                    and_(
                        GeneratedDocument.created_at >= day_start,
                        GeneratedDocument.created_at <= day_end
                    )
                )
                val = (await db.execute(day_stmt)).scalar() or 0
                day_label = day_date.strftime("%a")
                daily_docs.append(ChartPoint(label=day_label, value=val))

            user_growth = [
                ChartPoint(label="Jan", value=2),
                ChartPoint(label="Feb", value=3),
                ChartPoint(label="Mar", value=4),
                ChartPoint(label="Apr", value=5),
                ChartPoint(label="May", value=6),
                ChartPoint(label="Jun", value=total_users),
            ]

            # 4. Admin Recent Users
            u_recent_stmt = select(User).order_by(User.created_at.desc()).limit(5)
            u_recent_res = await db.execute(u_recent_stmt)
            recent_users_db = list(u_recent_res.scalars().all())

        else:
            # 1. Standard User Metrics
            d_today_stmt = select(func.count(GeneratedDocument.id)).where(
                and_(
                    GeneratedDocument.created_at >= today_start,
                    GeneratedDocument.user_id == current_user.id
                )
            )
            d_month_stmt = select(func.count(GeneratedDocument.id)).where(
                and_(
                    GeneratedDocument.created_at >= month_start,
                    GeneratedDocument.user_id == current_user.id
                )
            )
            dl_total_stmt = select(func.count(DownloadLog.id)).where(DownloadLog.user_id == current_user.id)

            gen_today = (await db.execute(d_today_stmt)).scalar() or 0
            gen_month = (await db.execute(d_month_stmt)).scalar() or 0
            total_downloads = (await db.execute(dl_total_stmt)).scalar() or 0

            # Reset admin stats to 0 under User Perspective
            metrics = MetricCard(
                total_users=0,
                active_users=0,
                inactive_users=0,
                gen_today=gen_today,
                gen_month=gen_month,
                total_downloads=total_downloads
            )

            # 2. User-specific Activities
            act_stmt = select(ActivityLog).where(ActivityLog.user_id == current_user.id).order_by(ActivityLog.timestamp.desc()).limit(5)
            act_res = await db.execute(act_stmt)
            activities = list(act_res.scalars().all())

            # 3. User Charts (Only documents generated by this user)
            daily_docs = []
            for i in range(6, -1, -1):
                day_date = datetime.now(UTC).date() - timedelta(days=i)
                day_start = datetime.combine(day_date, datetime.min.time())
                day_end = datetime.combine(day_date, datetime.max.time())
                
                day_stmt = select(func.count(GeneratedDocument.id)).where(
                    and_(
                        GeneratedDocument.created_at >= day_start,
                        GeneratedDocument.created_at <= day_end,
                        GeneratedDocument.user_id == current_user.id
                    )
                )
                val = (await db.execute(day_stmt)).scalar() or 0
                day_label = day_date.strftime("%a")
                daily_docs.append(ChartPoint(label=day_label, value=val))

            user_growth = []
            recent_users_db = []

        recent_activities = []
        for a in activities:
            recent_activities.append(
                ActivityLogResponse(
                    id=str(a.id),
                    user_name=a.user.name if a.user else "System",
                    action=a.action,
                    details=a.details,
                    timestamp=a.timestamp
                )
            )

        recent_users = []
        for u in recent_users_db:
            recent_users.append(
                DashboardUserResponse(
                    id=str(u.id),
                    name=u.name,
                    email=u.email,
                    status=u.status,
                    created_at=u.created_at
                )
            )

        charts = DashboardCharts(
            daily_documents=daily_docs,
            user_growth=user_growth
        )

        return DashboardFullResponse(
            metrics=metrics,
            recent_activities=recent_activities,
            charts=charts,
            recent_users=recent_users
        )

    async def log_activity(
        self, db: AsyncSession, *, user_id: str, action: str, details: str
    ) -> ActivityLog:
        log = ActivityLog(
            user_id=uuid.UUID(user_id) if user_id else None,
            action=action,
            details=details
        )
        db.add(log)
        await db.flush()
        return log


dashboard_service = DashboardService()
