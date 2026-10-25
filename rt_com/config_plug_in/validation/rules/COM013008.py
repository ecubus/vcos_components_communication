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
"""COM013008: Tx IPdu must configure ComTxModeFalse (codegen hard-depends on it).

Do not invent the container in the generator filter — fail at verify instead.
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


def _child_by_def_suffix(parent: dict, def_name: str):
    """Return (key, child_dict) for a nested container whose DefinitionRef ends with def_name."""
    if not isinstance(parent, dict):
        return None, None
    # Prefer exact short-name key when present and typed correctly.
    direct = parent.get(def_name)
    if isinstance(direct, dict):
        dref = direct.get("DefinitionRef", "")
        if isinstance(dref, str) and (not dref or dref.split("/")[-1] == def_name):
            return def_name, direct
    for k, v in parent.items():
        if k in ("DefinitionRef", "Tag") or not isinstance(v, dict):
            continue
        dref = v.get("DefinitionRef", "")
        if isinstance(dref, str) and dref.split("/")[-1] == def_name:
            return k, v
    return None, None


class Com013008Rule(BasicRule):
    ruleset_name = "Com013008"
    validation_result = False

    def __init__(self, logs, bsw_ecuc_cfg_class_dict) -> None:
        super().__init__()
        self.logs = logs
        self.bsw_ecuc_cfg_class_dict = bsw_ecuc_cfg_class_dict
        self.ecuc_com_dict = bsw_ecuc_cfg_class_dict
        self.validation_code = self.__class__.ruleset_name
        self.validation_summary = (
            "Tx ComIPdu must have ComTxModeFalse container "
            "(Com codegen template requires it; configure False mode, do not invent in filter)"
        )
        self.durable_init()

    def durable_init(self):
        # 注：固定名称的规则集只能初始化一次，否则会异常报错
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

    def _needs_tx_mode_false(self, ipdu: dict) -> bool:
        """True when this IPdu is Tx (SEND) or already has ComTxModeTrue under ComTxIPdu."""
        direction = ""
        if isinstance(ipdu.get("ComIPduDirection"), dict):
            direction = ipdu["ComIPduDirection"].get("Value") or ""
        if direction == "SEND":
            return True
        _, tx_ipdu = _child_by_def_suffix(ipdu, "ComTxIPdu")
        if isinstance(tx_ipdu, dict):
            _, mode_true = _child_by_def_suffix(tx_ipdu, "ComTxModeTrue")
            if isinstance(mode_true, dict):
                return True
        return False

    def _has_tx_mode_false(self, ipdu: dict) -> bool:
        _, tx_ipdu = _child_by_def_suffix(ipdu, "ComTxIPdu")
        if not isinstance(tx_ipdu, dict):
            return False
        _, mode_false = _child_by_def_suffix(tx_ipdu, "ComTxModeFalse")
        return isinstance(mode_false, dict)

    @timing_decorator
    def validation_run(self):
        valid = True
        ecuc_com_dict = self.ecuc_com_dict
        if "Com" in ecuc_com_dict.keys():
            com_dict = ecuc_com_dict["Com"]["ArPackages"]["ActiveEcuC"]["Com"]
            com_config_dict = com_tools_get_dict_by_definition_ref(com_dict, "ComConfig")
        else:
            com_config_dict = com_tools_get_dict_by_definition_ref(ecuc_com_dict, "ComConfig")

        com_ipdu_dict = {}
        for key, value in com_config_dict.items():
            if key in ("DefinitionRef", "Tag") or not isinstance(value, dict):
                continue
            if value.get("DefinitionRef") == "/AUTOSAR/EcucDefs/Com/ComConfig/ComIPdu":
                com_ipdu_dict[key] = value

        base_path = "/ActiveEcuC/Com/ComConfig"

        for ipdu_name, ipdu in com_ipdu_dict.items():
            path = f"{base_path}/{ipdu_name}"
            if not self._needs_tx_mode_false(ipdu):
                continue
            if self._has_tx_mode_false(ipdu):
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    f"ComIPdu {ipdu_name} has ComTxModeFalse under ComTxIPdu",
                    path,
                    "pass",
                )
            else:
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    (
                        f"ComIPdu {ipdu_name} is Tx (or has ComTxModeTrue) but missing "
                        f"ComTxModeFalse container at {path}/ComTxIPdu/ComTxModeFalse; "
                        f"configure the False Tx mode container (codegen requires it)"
                    ),
                    path,
                    "fail",
                )
                valid = False
        return valid
