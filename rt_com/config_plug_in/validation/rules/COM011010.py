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
"""COM011010: ComIPdu must configure numeric ComIPduHandleId (codegen sort hard-depends).

Do not invent sequential HandleIds in the generator filter — fail at verify instead.
"""
from func_module.validation.common.basic_rule import BasicRule, timing_decorator
from durable.lang import *
from durable.engine import *


def com_tools_get_dict_by_definition_ref(input_dict: dict, definition_ref: str) -> dict:
    for k, v in input_dict.items():
        if isinstance(v, dict):
            if "DefinitionRef" in v.keys():
                if v["DefinitionRef"].split("/")[-1] == definition_ref:
                    return v
    return {}


def _has_numeric_handle(container: dict, key: str) -> bool:
    node = container.get(key) if isinstance(container, dict) else None
    if not isinstance(node, dict):
        return False
    val = node.get("Value")
    if val is None or val == "":
        return False
    try:
        int(val)
        return True
    except (TypeError, ValueError):
        return False


class Com011010Rule(BasicRule):
    ruleset_name = "Com011010"
    validation_result = False

    def __init__(self, logs, bsw_ecuc_cfg_class_dict) -> None:
        super().__init__()
        self.logs = logs
        self.bsw_ecuc_cfg_class_dict = bsw_ecuc_cfg_class_dict
        self.ecuc_com_dict = bsw_ecuc_cfg_class_dict
        self.validation_code = self.__class__.ruleset_name
        self.validation_summary = (
            "ComIPdu must have numeric ComIPduHandleId "
            "(Com codegen sorts by HandleId; configure it, do not invent in filter)"
        )
        self.durable_init()

    def durable_init(self):
        try:
            get_host().get_ruleset(self.__class__.ruleset_name)
        except Exception:
            with ruleset(self.__class__.ruleset_name):

                @when_all(+m.status)
                def event(c):
                    pass

                @when_all(+m.comipdu_name)
                def fact(c):
                    self.__class__.validation_result = True

    def check_validation_run(self):
        if not self.modules_are_exist(["Com"], self.bsw_ecuc_cfg_class_dict):
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
        ecuc_com_dict = self.ecuc_com_dict
        if "Com" in ecuc_com_dict.keys():
            com_dict = ecuc_com_dict["Com"]["ArPackages"]["ActiveEcuC"]["Com"]
            com_config_dict = com_tools_get_dict_by_definition_ref(com_dict, "ComConfig")
        else:
            com_config_dict = com_tools_get_dict_by_definition_ref(ecuc_com_dict, "ComConfig")

        base_path = "/ActiveEcuC/Com/ComConfig"
        for ipdu_name, ipdu in com_config_dict.items():
            if ipdu_name in ("DefinitionRef", "Tag") or not isinstance(ipdu, dict):
                continue
            if ipdu.get("DefinitionRef") != "/AUTOSAR/EcucDefs/Com/ComConfig/ComIPdu":
                continue
            path = f"{base_path}/{ipdu_name}/ComIPduHandleId"
            if _has_numeric_handle(ipdu, "ComIPduHandleId"):
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    f"ComIPdu {ipdu_name} has numeric ComIPduHandleId",
                    path,
                    "pass",
                )
            else:
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    (
                        f"ComIPdu {ipdu_name} missing numeric ComIPduHandleId at {path}; "
                        f"configure HandleId (codegen sort requires it; do not invent in filter)"
                    ),
                    path,
                    "fail",
                )
                valid = False
        return valid
