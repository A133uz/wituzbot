import enum

#class EventTypeEnum(enum.Enum):
#    online = "online"
#    in_person = "in_person"

class EventTypeEnum(str, enum.Enum):
    online = "online"
    in_person = "in_person"