import enum


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    QUALIFIED = "QUALIFIED"
    NEEDS_INFO = "NEEDS_INFO"
    DISQUALIFIED = "DISQUALIFIED"
    CONTACTED = "CONTACTED"
    MEETING_BOOKED = "MEETING_BOOKED"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


class ScoreLabel(str, enum.Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class LeadSource(str, enum.Enum):
    WEB_FORM = "web_form"
    WEBSITE = "website"
    REFERRAL = "referral"
    OUTBOUND = "outbound"
    EVENT = "event"
    PARTNER = "partner"
    LINKEDIN = "linkedin"
    WEBINAR = "webinar"
    TRADE_SHOW = "trade_show"
    CONFERENCE = "conference"
    COLD_EMAIL = "cold_email"
    GOOGLE_ADS = "google_ads"
    ACCELERATOR = "accelerator"
    STARTUP_ACCELERATOR = "startup_accelerator"
    STARTUP_COMPETITION = "startup_competition"
    FOUNDATION_GRANT = "foundation_grant"
    Y_COMBINATOR = "y_combinator"
    DARK_WEB = "dark_web"


class Urgency(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, enum.Enum):
    SEND_EMAIL = "SEND_EMAIL"
    ASK_QUESTION = "ASK_QUESTION"
    DISQUALIFY = "DISQUALIFY"
    HOLD = "HOLD"


class ActivityType(str, enum.Enum):
    INGESTED = "INGESTED"
    ENRICHED = "ENRICHED"
    SCORED = "SCORED"
    EMAIL_DRAFTED = "EMAIL_DRAFTED"
    EMAIL_SENT = "EMAIL_SENT"
    EMAIL_REPLIED = "EMAIL_REPLIED"
    STATUS_CHANGED = "STATUS_CHANGED"
    NOTE = "NOTE"
    ERROR = "ERROR"
    REPLY_CLASSIFIED = "REPLY_CLASSIFIED"
    CLASSIFICATION_OVERRIDDEN = "CLASSIFICATION_OVERRIDDEN"
    CALENDLY_LINK_SENT = "CALENDLY_LINK_SENT"
    DEMO_BOOKED = "DEMO_BOOKED"


class ReplyClassification(str, enum.Enum):
    INTERESTED_BOOK_DEMO = "INTERESTED_BOOK_DEMO"
    NOT_INTERESTED = "NOT_INTERESTED"
    QUESTION = "QUESTION"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    UNCLEAR = "UNCLEAR"


class OutcomeType(str, enum.Enum):
    BOOKED_DEMO = "booked_demo"
    NO_RESPONSE = "no_response"
    DISQUALIFIED = "disqualified"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class OutcomeStage(str, enum.Enum):
    EMAIL_SENT = "EMAIL_SENT"
    RESPONDED = "RESPONDED"
    NO_RESPONSE = "NO_RESPONSE"
    BOOKED_DEMO = "BOOKED_DEMO"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"
    DISQUALIFIED = "DISQUALIFIED"


class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    BOUNCED = "BOUNCED"
    FAILED = "FAILED"


class EmailVariant(str, enum.Enum):
    FIRST_TOUCH = "first_touch"
    FOLLOW_UP_1 = "follow_up_1"
    FOLLOW_UP_2 = "follow_up_2"
    BREAKUP = "breakup"


class ProcessingStatus(str, enum.Enum):
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"


class PipelineRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
