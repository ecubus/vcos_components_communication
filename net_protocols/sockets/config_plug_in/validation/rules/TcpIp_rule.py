import importlib
from func_module.validation.common.validation_def import ValidationData, ExceptionRuleLog
from sockets.config_plug_in.validation.rules.TcpIp011001 import TcpIp011001Rule
from sockets.config_plug_in.validation.rules.TcpIp011002 import TcpIp011002Rule
from sockets.config_plug_in.validation.rules.TcpIp011003 import TcpIp011003Rule
from sockets.config_plug_in.validation.rules.TcpIp011004 import TcpIp011004Rule
from sockets.config_plug_in.validation.rules.TcpIp011005 import TcpIp011005Rule
from sockets.config_plug_in.validation.rules.TcpIp012001 import TcpIp012001Rule
from sockets.config_plug_in.validation.rules.TcpIp012002 import TcpIp012002Rule
from sockets.config_plug_in.validation.rules.TcpIp012003 import TcpIp012003Rule
from sockets.config_plug_in.validation.rules.TcpIp016001 import TcpIp016001Rule
from sockets.config_plug_in.validation.rules.TcpIp016002 import TcpIp016002Rule
from sockets.config_plug_in.validation.rules.TcpIp016003 import TcpIp016003Rule
from sockets.config_plug_in.validation.rules.TcpIp110001 import TcpIp110001Rule

VALIDATE_MARK_LIST = [
    "012001", "012002", "012003", "016002", "016003", "110001"
]
class TcpIpRule():

    def __init__(self) -> None:
        self.logs = {}
        self.ecu_cfg = None

    def validate(self, validation_data: ValidationData):

        bsw_ecuc_cfg_class_dict = validation_data.bsw_ecuc_dict

        for validate_code in VALIDATE_MARK_LIST:
            validate_rule_package = importlib.import_module(f'sockets.config_plug_in.validation.rules.TcpIp{validate_code}')
            validate_rule_class = getattr(validate_rule_package, f'TcpIp{validate_code}Rule')
            try:
                bsw_module_rule_obj = validate_rule_class(self.logs, bsw_ecuc_cfg_class_dict)
                # 校验当前校验规则的前置条件是否满足
                if bsw_module_rule_obj.check_validation_run():
                    bsw_module_rule_obj.validation_run()
            except Exception as e:
                ExceptionRuleLog.set_rule_exception_log(self.logs, "TcpIp", validate_code, f"{type(e)}: {str(e)}")
        return self.logs
