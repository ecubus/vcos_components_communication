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
"""COM013009: Tx IPdu must configure ComTxIPdu and ComTxModeTrue (codegen hard-depends).

Do not invent ComTxModeTrue in the generator filter — fail at verify instead.
Pairs with COM013008 (ComTxModeFalse).
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


class Com013009Rule(BasicRule):
    ruleset_name = "Com013009"
    validation_result = False

    def __init__(self, logs, bsw_ecuc_cfg_class_dict) -> None:
        super().__init__()
        self.logs = logs
        self.bsw_ecuc_cfg_class_dict = bsw_ecuc_cfg_class_dict
        self.ecuc_com_dict = bsw_ecuc_cfg_class_dict
        self.validation_code = self.__class__.ruleset_name
        self.validation_summary = (
            "Tx ComIPdu must have ComTxIPdu/ComTxModeTrue "
            "(Com codegen requires True mode; configure it, do not invent in filter)"
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

    def _is_tx(self, ipdu: dict) -> bool:
        direction = ""
        if isinstance(ipdu.get("ComIPduDirection"), dict):
            direction = ipdu["ComIPduDirection"].get("Value") or ""
        if direction == "SEND":
            return True
        _, tx_ipdu = _child_by_def_suffix(ipdu, "ComTxIPdu")
        if isinstance(tx_ipdu, dict):
            _, mode_false = _child_by_def_suffix(tx_ipdu, "ComTxModeFalse")
            if isinstance(mode_false, dict):
                return True
        return False

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
            if not self._is_tx(ipdu):
                continue
            path = f"{base_path}/{ipdu_name}"
            _, tx_ipdu = _child_by_def_suffix(ipdu, "ComTxIPdu")
            if not isinstance(tx_ipdu, dict):
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    (
                        f"ComIPdu {ipdu_name} is Tx but missing ComTxIPdu at "
                        f"{path}/ComTxIPdu; configure ComTxIPdu (codegen requires it)"
                    ),
                    path,
                    "fail",
                )
                valid = False
                continue
            _, mode_true = _child_by_def_suffix(tx_ipdu, "ComTxModeTrue")
            if isinstance(mode_true, dict):
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    f"ComIPdu {ipdu_name} has ComTxModeTrue under ComTxIPdu",
                    f"{path}/ComTxIPdu/ComTxModeTrue",
                    "pass",
                )
            else:
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    (
                        f"ComIPdu {ipdu_name} is Tx but missing ComTxModeTrue at "
                        f"{path}/ComTxIPdu/ComTxModeTrue; configure True Tx mode "
                        f"(codegen requires it; do not invent in filter)"
                    ),
                    f"{path}/ComTxIPdu/ComTxModeTrue",
                    "fail",
                )
                valid = False
        return valid
