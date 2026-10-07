"""
Notification service for in-app notifications.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.models.match import Match


class NotificationService:
    """
    Service for creating in-app notifications.
    """
    
    async def create_notification(
        self,
        db: AsyncSession,
        user_id: str,
        notification_type: NotificationType,
        subject: str,
        body: str,
        related_item_id: Optional[str] = None,
        related_match_id: Optional[str] = None
    ) -> Notification:
        """
        Create and store a notification record.
        
        Args:
            db: Database session
            user_id: Recipient user ID
            notification_type: Type of notification
            subject: Notification subject
            body: Notification body
            related_item_id: Optional related item
            related_match_id: Optional related match
        
        Returns:
            Created Notification object
        """
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type.value,
            subject=subject,
            body=body,
            related_item_id=related_item_id,
            related_match_id=related_match_id,
            is_sent=True  # In-app notifications are always "sent"
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        return notification
    
    async def notify_match_found(
        self,
        db: AsyncSession,
        user: User,
        match: Match,
        item_title: str
    ) -> Notification:
        """
        Send notification when a potential match is found.
        
        Args:
            db: Database session
            user: User to notify
            match: The match that was found
            item_title: Title of the matched item
        
        Returns:
            Created Notification
        """
        subject = "تم العثور على تطابق محتمل لبلاغك"
        distance_text = (
            f"{match.distance_km:.1f} كم"
            if match.distance_km is not None
            else "غير محددة"
        )
        body = f"""
مرحبًا {user.full_name or 'بك'}،

وجدنا تطابقًا محتملًا لبلاغك: {item_title}

نسبة التطابق: {match.overall_score:.0%}
المسافة: {distance_text}

سجّل الدخول لمراجعة التطابق وتأكيده إذا كان الغرض يعود لك.

مع تحيات،
فريق مستردات
        """.strip()
        
        return await self.create_notification(
            db=db,
            user_id=user.id,
            notification_type=NotificationType.MATCH_FOUND,
            subject=subject,
            body=body,
            related_match_id=match.id
        )
    
    async def notify_match_confirmed(
        self,
        db: AsyncSession,
        user: User,
        match: Match,
        confirmer_name: str
    ) -> Notification:
        """
        Send notification when the other party confirms a match.
        
        Args:
            db: Database session
            user: User to notify
            match: The confirmed match
            confirmer_name: Name of the person who confirmed
        
        Returns:
            Created Notification
        """
        subject = "تم تأكيد التطابق، وننتظر تأكيدك"
        body = f"""
مرحبًا {user.full_name or 'بك'}،

خبر رائع! أكّد {confirmer_name} هذا التطابق.

سجّل الدخول وأكّد التطابق من طرفك. بعد تأكيد الطرفين ستظهر بيانات التواصل لكل طرف.

مع تحيات،
فريق مستردات
        """.strip()
        
        return await self.create_notification(
            db=db,
            user_id=user.id,
            notification_type=NotificationType.MATCH_CONFIRMED,
            subject=subject,
            body=body,
            related_match_id=match.id
        )
    
    async def notify_contact_revealed(
        self,
        db: AsyncSession,
        user: User,
        other_user: User,
        match: Match
    ) -> Notification:
        """
        Send notification when both parties confirm and contact is revealed.
        
        Args:
            db: Database session
            user: User to notify
            other_user: The other party
            match: The confirmed match
        
        Returns:
            Created Notification
        """
        subject = "أصبحت بيانات التواصل متاحة"
        body = f"""
مرحبًا {user.full_name or 'بك'}،

تم تأكيد التطابق من الطرفين. هذه بيانات التواصل:

الاسم: {other_user.full_name or 'غير متوفر'}
البريد الإلكتروني: {other_user.email}
الهاتف: {other_user.phone_number or 'غير متوفر'}

تواصل مع الطرف الآخر لترتيب استعادة الغرض.

مع تحيات،
فريق مستردات
        """.strip()
        
        return await self.create_notification(
            db=db,
            user_id=user.id,
            notification_type=NotificationType.CONTACT_REVEALED,
            subject=subject,
            body=body,
            related_match_id=match.id
        )


# Singleton instance
notification_service = NotificationService()
