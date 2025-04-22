# ##############################################################################
# components/communication/eth_stack/CMakeLists.txt
#
# Copyright (c) 2025 Li Auto Inc. and its affiliates
# Licensed under the Apache License, Version 2.0(the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ##############################################################################

if(CONFIG_ETH_STACK)
if(DEFINED BOARD_NAME)
  if(${BOARD_NAME} MATCHES "A2G_TC397_5V_TFT")
      set(GENDATA_DIR "${NUTTX_APPS_DIR}/${APPS_DIR}/platform_cfg/tc397_cfg/gen_data")
  endif()
  if(${BOARD_NAME} MATCHES "E3650_DEV_KIT")
      set(GENDATA_DIR "${NUTTX_APPS_DIR}/${APPS_DIR}/platform_cfg/e3650_cfg/gen_data")
  endif()
else()
  set(GENDATA_DIR "${NUTTX_APPS_DIR}/${APPS_DIR}/cfg_prj/gen_data")
endif()

  # 头文件引入
  set( INCLUDE_DIR

    # GENERAL
    ${NUTTX_APPS_DIR}/components/include/autosar/
    ${GENDATA_DIR}/Os
    ${GENDATA_DIR}/Memmap
    ${GENDATA_DIR}/EthIf
    ${GENDATA_DIR}/Lwip
    ${GENDATA_DIR}/TcpIp
    ${NUTTX_APPS_DIR}/${APPS_DIR}/apps
    ${NUTTX_APPS_DIR}/components/rt_framework/inc
    ${NUTTX_APPS_DIR}/components/maintaining/vcos_log/inc
    ${NUTTX_APPS_DIR}/${APPS_DIR}/apps/mvbs_app/mvbs_adapter/dds_autosar_intf/

    ${CMAKE_CURRENT_SOURCE_DIR}
    ${NUTTX_APPS_DIR}/components/include/
    ${NUTTX_APPS_DIR}/components/communication/net_protocols/sockets/
  )

  if (CONFIG_SIM_ETH_DRIVER)
    list(APPEND INCLUDE_DIR
      ${NUTTX_APPS_DIR}/components/include/autosar/
      ${NUTTX_APPS_DIR}/drivers/sim/eth/inc
      ${NUTTX_CHIP_ABS_DIR}/driver/eth/inc
    )
  elseif(CONFIG_ARCH_CHIP_E3650)
    list(APPEND INCLUDE_DIR
      ${ETH_STACK_E3XX_GETHMAC_DIR}/e3650
    )
  else()
  endif()

  # 收集 EthIf 目录下的所需 .c 文件
  file(GLOB C_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/*.c"
    "${GENDATA_DIR}/EthIf/*.c"
  )

  # 合并所有源文件
  set( ETH_STACK_SRCS
    ${C_SOURCES}
  )

  if ((CMAKE_C_COMPILER_ID STREQUAL "GNU") AND (NOT CONFIG_SIM_ETH_DRIVER))
    add_compile_options(-Wno-undef)
    add_compile_options(-Werror)
  endif()

  nuttx_add_library(eth_if STATIC)
  target_sources(eth_if PRIVATE ${ETH_STACK_SRCS})
  target_include_directories(eth_if PRIVATE ${INCLUDE_DIR})

  target_include_directories(eth_if SYSTEM PRIVATE
    "${LWIP_2_1_3_DIR}/src/include"               # lwIP 官方 include
    "${EXTERNAL_DIR}/lwip/lwip_osal"  # OSAL/移植层 (sys_arch.h 等)
    "${EXTERNAL_DIR}/lwip"          # 顶层(有 lwipopts.h, Lwip.h, ethernetif.h 等)
  )
  if (NOT CONFIG_SIM_ETH_DRIVER)
    target_link_libraries(eth_if PRIVATE eth_gethmac)
  endif()
endif()
