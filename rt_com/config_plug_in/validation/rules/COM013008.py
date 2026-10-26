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
"""COM013008: ComTxModeFalse required only when TMS / ComFilter false-path is used.

BSWMD lower=0. AUTOSAR: False mode applies when ComFilter evaluates to false.
Without TMS (no active ComFilter on Tx signals), False is optional — codegen may
mirror True into the false_cfg slot. Do not FAIL every SEND IPdu.
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


_ALWAYS_FILTERS = {"ALWAYS", "COM_ALWAYS", "", None}


def _filter_algorithm(filter_node: dict):
    if not isinstance(filter_node, dict):
        return None
    algo = filter_node.get("ComFilterAlgorithm")
    if isinstance(algo, dict):
        return algo.get("Value")
    # nested / alternate short-name
    _, algo2 = _child_by_def_suffix(filter_node, "ComFilterAlgorithm")
    if isinstance(algo2, dict):
        return algo2.get("Value")
    return None


def _signal_has_active_filter(signal: dict) -> bool:
    """True when ComFilter is present with algorithm other than ALWAYS (TMS false-path)."""
    if not isinstance(signal, dict):
        return False
    _, filt = _child_by_def_suffix(signal, "ComFilter")
    if not isinstance(filt, dict):
        return False
    algo = _filter_algorithm(filt)
    if algo in _ALWAYS_FILTERS:
        return False
    # Filter container present without ALWAYS → treat as TMS-capable
    return True


def _short_name_from_ref(ref) -> str:
    if not isinstance(ref, str) or not ref:
        return ""
    return ref.split("/")[-1]


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
            "ComTxModeFalse required only when TMS/ComFilter false-path is used "
            "(BSWMD optional otherwise; do not force on every Tx)"
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
        return isinstance(tx_ipdu, dict)

    def _collect_signals(self, com_config_dict: dict) -> dict:
        signals = {}
        for name, node in com_config_dict.items():
            if name in ("DefinitionRef", "Tag") or not isinstance(node, dict):
                continue
            dref = node.get("DefinitionRef", "")
            if isinstance(dref, str) and dref.split("/")[-1] in ("ComSignal", "ComSignalGroup"):
                signals[name] = node
        return signals

    def _ipdu_tms_required(self, ipdu: dict, signals: dict) -> bool:
        """TMS false-path needed if any referenced Tx signal has an active ComFilter."""
        refs = []
        sig_ref = ipdu.get("ComIPduSignalRef")
        if isinstance(sig_ref, dict):
            vr = sig_ref.get("ValueRef")
            if isinstance(vr, str) and vr:
                refs.append(vr)
            elif isinstance(vr, list):
                refs.extend([r for r in vr if isinstance(r, str) and r])
        for ref in refs:
            sig = signals.get(_short_name_from_ref(ref))
            if sig is None:
                # try full walk match by suffix
                for sname, snode in signals.items():
                    if sname == _short_name_from_ref(ref) or ref.endswith("/" + sname):
                        sig = snode
                        break
            if _signal_has_active_filter(sig):
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

        signals = self._collect_signals(com_config_dict)
        base_path = "/ActiveEcuC/Com/ComConfig"

        for ipdu_name, ipdu in com_config_dict.items():
            if ipdu_name in ("DefinitionRef", "Tag") or not isinstance(ipdu, dict):
                continue
            if ipdu.get("DefinitionRef") != "/AUTOSAR/EcucDefs/Com/ComConfig/ComIPdu":
                continue
            if not self._is_tx(ipdu):
                continue
            path = f"{base_path}/{ipdu_name}"
            tms = self._ipdu_tms_required(ipdu, signals)
            has_false = self._has_tx_mode_false(ipdu)
            if not tms:
                # Optional: codegen may mirror True → false_cfg; no FAIL
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    (
                        f"ComIPdu {ipdu_name}: no active ComFilter/TMS — "
                        f"ComTxModeFalse optional (present={has_false})"
                    ),
                    path,
                    "pass",
                )
                continue
            if has_false:
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    f"ComIPdu {ipdu_name} has TMS/ComFilter and ComTxModeFalse",
                    f"{path}/ComTxIPdu/ComTxModeFalse",
                    "pass",
                )
            else:
                self.vlog(
                    self.validation_code,
                    self.validation_summary,
                    (
                        f"ComIPdu {ipdu_name} uses TMS/ComFilter (false-path) but missing "
                        f"ComTxModeFalse at {path}/ComTxIPdu/ComTxModeFalse; configure it"
                    ),
                    f"{path}/ComTxIPdu/ComTxModeFalse",
                    "fail",
                )
                valid = False
        return valid
