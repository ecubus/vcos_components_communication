# This Python file uses the following encoding: utf-8
# ##############################################################################
# Copyright (c) 2025 Li Auto Inc. and its affiliates
# Licensed under the Apache License, Version 2.0(the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ##############################################################################
"""CanSM016002: CanSMDevErrorDetect is BSWMD required (lowerMultiplicity=1, ECUC_CanSM_00133).

Do not invent false in the generator filter — FAIL at verify when missing/empty.
"""
from func_module.validation.common.basic_rule import BasicRule, timing_decorator
from durable.lang import *
from durable.engine import *


def _get_name(definition_ref) -> str:
    if not isinstance(definition_ref, str):
        return ""
    return definition_ref.split("/")[-1]


def _has_bool_value(node) -> bool:
    if not isinstance(node, dict):
        return False
    val = node.get("Value")
    if val is None or val == "":
        return False
    return True


class CanSM016002Rule(BasicRule):
    ruleset_name = "CanSM016002"
    validation_result = False

    def __init__(self, logs, bsw_ecuc_cfg_class_dict) -> None:
        super().__init__()
        self.logs = logs
        self.validation_code = self.__class__.ruleset_name
        self.validation_summary = (
            "CanSMGeneral must configure CanSMDevErrorDetect "
            "(BSWMD lowerMultiplicity=1; do not invent in filter)"
        )
        self.bsw_ecuc_cfg_class_dict = bsw_ecuc_cfg_class_dict
        self.durable_init()

    def durable_init(self):
        try:
            get_host().get_ruleset(self.__class__.ruleset_name)
        except Exception:
            with ruleset(self.__class__.ruleset_name):

                @when_all(+m.status)
                def event(c):
                    pass

                @when_all(+m.frame_id)
                def fact(c):
                    self.__class__.validation_result = True

    def check_validation_run(self):
        if not self.modules_are_exist(["CanSM"], self.bsw_ecuc_cfg_class_dict):
            self.vlog(
                self.validation_code,
                self.validation_summary,
                "Data required for validation is missing",
                self.validation_summary,
                "fail",
            )
            return False
        return True

    @timing_decorator
    def validation_run(self):
        valid = True
        cansm = self.bsw_ecuc_cfg_class_dict["CanSM"]["ArPackages"]["ActiveEcuC"]["CanSM"]
        found_general = False
        for name, item in cansm.items():
            if name == "DefinitionRef" or not isinstance(item, dict):
                continue
            if _get_name(item.get("DefinitionRef")) != "CanSMGeneral":
                continue
            found_general = True
            path = f"/ActiveEcuC/CanSM/{name}/CanSMDevErrorDetect"
            node = item.get("CanSMDevErrorDetect")
            if not isinstance(node, dict):
                # DefinitionRef-suffix fallback
                for k, v in item.items():
                    if k in ("DefinitionRef", "Tag") or not isinstance(v, dict):
                        continue
                    if _get_name(v.get("DefinitionRef")) == "CanSMDevErrorDetect":
                        node = v
                        path = f"/ActiveEcuC/CanSM/{name}/{k}"
                        break
            if _has_bool_value(node):
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    f"CanSMDevErrorDetect configured (Value={node.get('Value')})",
                    path,
                    "pass",
                )
            else:
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    (
                        f"CanSMGeneral missing CanSMDevErrorDetect at {path}; "
                        f"configure true/false (BSWMD required; do not invent in filter)"
                    ),
                    path,
                    "fail",
                )
                valid = False
        if not found_general:
            self.vlog(
                self.validation_code,
                self.validation_summary,
                "Cannot find CanSMGeneral container",
                "/ActiveEcuC/CanSM/",
                "fail",
            )
            valid = False
        return valid

    def add_rule_time(self):
        pass
