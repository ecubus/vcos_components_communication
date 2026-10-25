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
"""PduR016011: PduRDestPdu must configure PduRDestPduDataProvision.

PduR016001 (and generator filter) read this enum. Missing key must be a clear
verify FAIL, never a Python KeyError / rule exception.
"""
from func_module.validation.common.basic_rule import BasicRule, timing_decorator
from durable.lang import *
from durable.engine import *
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from .PduR_rule_func import pdur_validate_get_routing_path


def _data_provision_value(pdurdestpdu: dict):
    """Return Value string if PduRDestPduDataProvision is present and non-empty, else None."""
    if not isinstance(pdurdestpdu, dict):
        return None
    node = pdurdestpdu.get("PduRDestPduDataProvision")
    if not isinstance(node, dict):
        # Fall back: find by DefinitionRef suffix (SHORT-NAME may differ)
        for k, v in pdurdestpdu.items():
            if k in ("DefinitionRef", "Tag") or not isinstance(v, dict):
                continue
            dref = v.get("DefinitionRef", "")
            if isinstance(dref, str) and dref.split("/")[-1] == "PduRDestPduDataProvision":
                node = v
                break
        else:
            return None
    val = node.get("Value")
    if val is None or str(val).strip() == "":
        return None
    return val


class PduR016011Rule(BasicRule):
    ruleset_name = "PduR016011"
    validation_result = False

    def __init__(self, logs, bsw_ecuc_cfg_class_dict) -> None:
        super().__init__()
        self.logs = logs
        self.validation_code = self.__class__.ruleset_name
        self.validation_summary = (
            "PduRDestPdu must have PduRDestPduDataProvision "
            "(configure enum; verify must FAIL clearly, never KeyError)"
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
        if not self.modules_are_exist(["PduR"], self.bsw_ecuc_cfg_class_dict):
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
        valid_all = True
        ecuc_pdur_dict = self.bsw_ecuc_cfg_class_dict["PduR"]["ArPackages"]["ActiveEcuC"]["PduR"]
        PduRRoutingPaths, PduRRoutingPaths_Name, ok = pdur_validate_get_routing_path(ecuc_pdur_dict)
        if ok is False:
            self.vlog(
                self.validation_code,
                self.validation_summary,
                "Cannot Find Container PduRRoutingPaths!",
                "/ActiveEcuC/PduR/",
                "fail",
            )
            return False

        dest_suffix = "/AUTOSAR/EcucDefs/PduR/" + PduRRoutingPaths_Name + "/PduRDestPdu"
        for name, pdurdestpdu in PduRRoutingPaths.items():
            if not isinstance(pdurdestpdu, dict):
                continue
            if pdurdestpdu.get("DefinitionRef") != dest_suffix:
                continue
            # Same gate as PduR016001: only DestPdus with a DestPduRef
            if not AutosarUtil.get_by_path_from_dict(pdurdestpdu, "/PduRDestPduRef/ValueRef"):
                continue
            path = "/ActiveEcuC/PduR/" + PduRRoutingPaths_Name + "/PduRDestPdu/" + name
            if _data_provision_value(pdurdestpdu) is None:
                valid_all = False
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    f"PduRDestPdu[{name}] missing PduRDestPduDataProvision "
                    f"(must configure PDUR_DIRECT or PDUR_TRIGGERTRANSMIT)!",
                    path,
                    "fail",
                )
            else:
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    f"PduRDestPdu[{name}] has PduRDestPduDataProvision",
                    path,
                    "pass",
                )
        return valid_all

    def add_rule_time(self):
        pass
