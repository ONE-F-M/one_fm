from lms.overrides.user import *

class UserOverrideLMS(CustomUser):
    def validate_username_characters(self):
        pass