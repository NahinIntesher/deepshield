import datetime as dt
from sqlalchemy import Column,String,Integer,Text,DateTime,Float,Boolean,ForeignKey
from .database import Base
class Scan(Base):
 __tablename__='scans'
 id=Column(String(40),primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),index=True,nullable=False)
 name=Column(String(256),nullable=False)
 source=Column(String(16),nullable=False)
 url=Column(Text)
 path=Column(Text)
 cache_key=Column(String(64),index=True)
 state=Column(String(20),default='queued')
 message=Column(Text,default='Waiting for the trained detector')
 result_id=Column(Integer,ForeignKey('detection_records.id'))
 created_at=Column(DateTime,default=dt.datetime.utcnow)
class Charge(Base):
 __tablename__='scan_charges'
 id=Column(String(40),primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),index=True,nullable=False)
 charged=Column(Boolean,default=True)
 created_at=Column(DateTime,default=dt.datetime.utcnow,index=True)
class Membership(Base):
 __tablename__='memberships'
 user_id=Column(Integer,ForeignKey('users.id'),primary_key=True)
 expires=Column(DateTime)
 activation=Column(String(32),default='none')
class Subscription(Base):
 __tablename__='subscription_requests'
 id=Column(Integer,primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
 reference=Column(String(160),default='')
 note=Column(Text,nullable=False)
 status=Column(String(20),default='pending')
 review=Column(Text,default='')
 created_at=Column(DateTime,default=dt.datetime.utcnow)
class ExtensionToken(Base):
 __tablename__='product_extension_tokens'
 token_hash=Column(String(64),primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
 kind=Column(String(16),nullable=False)
 expires=Column(Float,nullable=False)
class Ticket(Base):
 __tablename__='support_tickets'
 id=Column(Integer,primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
 subject=Column(String(160),nullable=False)
 message=Column(Text,nullable=False)
 reply=Column(Text,default='')
 status=Column(String(16),default='open')
 created_at=Column(DateTime,default=dt.datetime.utcnow)
class Notice(Base):
 __tablename__='notifications'
 id=Column(Integer,primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
 title=Column(String(160),nullable=False)
 message=Column(Text,nullable=False)
 read=Column(Boolean,default=False)
 created_at=Column(DateTime,default=dt.datetime.utcnow)
class Assessment(Base):
 __tablename__='learning_assessments'
 id=Column(String(40),primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),unique=True,nullable=False)
 state=Column(String(16),default='pre')
 assignment=Column(Text,nullable=False)
 pre_answers=Column(Text)
 post_answers=Column(Text)
 pre_score=Column(Float)
 post_score=Column(Float)
 exposures=Column(Integer,default=0)
 started_at=Column(DateTime,default=dt.datetime.utcnow)
 pre_at=Column(DateTime)

class GoogleIdentity(Base):
 __tablename__='google_identities'
 subject=Column(String(255),primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),unique=True,nullable=False)
 created_at=Column(DateTime,default=dt.datetime.utcnow)

class PendingRegistration(Base):
 __tablename__='pending_registrations'
 token_hash=Column(String(64),primary_key=True)
 username=Column(String(64),unique=True,nullable=False)
 email=Column(String(254),unique=True,nullable=False)
 display_name=Column(String(64),nullable=False)
 password_hash=Column(String(255),nullable=False)
 expires=Column(Float,nullable=False)
 sent_at=Column(Float,nullable=False)
 language=Column(String(2),nullable=False,default='en')

class PaymentReceipt(Base):
 __tablename__='payment_receipts'
 reference_hash=Column(String(64),primary_key=True)
 created_at=Column(DateTime,default=dt.datetime.utcnow)

class Lesson(Base):
 __tablename__='lessons'
 id=Column(Integer,primary_key=True)
 content_en=Column(Text,nullable=False)
 content_bn=Column(Text,nullable=False)
 correct_choice=Column(Integer,nullable=False)
 archived=Column(Boolean,default=False,nullable=False)
 created_at=Column(DateTime,default=dt.datetime.utcnow)
