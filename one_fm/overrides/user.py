from frappe.core.doctype.user.user import *
# from lms.overrides.user import *
from one_fm.utils import custom_toggle_notifications

# class UserOverrideLMS(CustomUser):
#     def validate_username_characters(self):
#         pass
    
    
class UserOverride(User):
    pass
    # def validate(self):
    #     self.__new_password = self.new_password
    #     self.new_password = ""

    #     if not frappe.flags.in_test:
    #         self.password_strength_test()

    #     if self.name not in STANDARD_USERS:
    #         self.validate_email_type(self.email)
    #         self.validate_email_type(self.name)
    #     self.add_system_manager_role()
    #     self.populate_role_profile_roles()
    #     self.check_roles_added()
    #     self.set_system_user()
    #     self.set_full_name()
    #     self.check_enable_disable()
    #     self.ensure_unique_roles()
    #     self.remove_all_roles_for_guest()
    #     self.validate_username()
    #     self.remove_disabled_roles()
    #     self.validate_user_email_inbox()
    #     ask_pass_update()
    #     self.validate_allowed_modules()
    #     self.validate_user_image()
    #     self.set_time_zone()

    #     if self.language == "Loading...":
    #         self.language = None

    #     if (self.name not in ["Administrator", "Guest"]) and (
    #         not self.get_social_login_userid("frappe")
    #     ):
    #         self.set_social_login_userid("frappe", frappe.generate_hash(length=39))
            
            
    # def check_enable_disable(self):
    #     # do not allow disabling administrator/guest
    #     if not cint(self.enabled) and self.name in STANDARD_USERS:
    #         frappe.throw(_("User {0} cannot be disabled").format(self.name))

    #     if not cint(self.enabled):
    #         self.a_system_manager_should_exist()

    #     # clear sessions if disabled
    #     if not cint(self.enabled) and getattr(frappe.local, "login_manager", None):
    #         frappe.local.login_manager.logout(user=self.name)

    #     # toggle notifications based on the user's status
    #     custom_toggle_notifications(self.name, enable=cint(self.enabled))