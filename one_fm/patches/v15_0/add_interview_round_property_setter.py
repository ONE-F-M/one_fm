from one_fm.custom.property_setter.interview_round import get_interview_round_properties
from one_fm.setup.setup import add_property_setter


def execute():
    add_property_setter(get_interview_round_properties())
