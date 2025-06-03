/*
 * Copyright (c) 2025 Li Auto Inc. and its affiliates
 * Licensed under the Apache License, Version 2.0(the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "ethernetif.h"

#include "lwip/opt.h"
#include <lwip/netifapi.h>
#include <string.h>
#include "lwip/def.h"
#include "lwip/snmp.h"
#include "lwip/pbuf.h"
#include "netif/etharp.h"
#include "lwip/inet.h"
#include "lwip/ip4.h"
#include "comstack_types.h"
#include "tcpip_types.h"

#if (CONFIG_MODULE_ETHIF == 1)
#include "ethif.h"
#endif

#define IFNAME0 'A'
#define IFNAME1 'R'
#define LWIP_ETH_HEADER_SIZE 14u
#define LWIP_ETH_MAC_ADDR_SIZE 6u
#define LWIP_ETH_FRAMETYPE_SIZE 2u

#define IPH_TOS_GET(hdr) (hdr)->_tos
#define IPH_PROTO_GET(hdr) (hdr)->_proto

#if (CONFIG_MODULE_ETHIF == 1)
extern tcpip_socket_id_type tcpip_buf_idx_to_socket_id[ETHIf_MAX_TXBUFSTOTAL];
#endif

#define TCPIP_START_SEC_CODE
#include "tcpip_memmap.h"
FUNC(void, TCPIP_CODE) lwip_set_phys_addr(struct netif *netif, const uint8* phys_addr_ptr){
    uint8 i;
#if (CONFIG_MODULE_ETHIF == 1)
    lwip_netif_ctrl_type *netif_ctrl = (lwip_netif_ctrl_type *)netif->hostname;
#endif

    for(i = 0; i < NETIF_MAX_HWADDR_LEN; i++) {
        netif->hwaddr[i] =  phys_addr_ptr[i];
    }
#if (CONFIG_MODULE_ETHIF == 1)
    ethif_set_phys_addr(netif_ctrl->ctrl_id, phys_addr_ptr);
#endif
}

/**
 * @brief  Frames reception function
 * @param  ctrl_idx
 * @param  frame_type
 * @param  is_broadcast
 * @param  phys_addr_ptr
 * @param  data_ptr
 * @param  len_byte
 * @retval None
 */
FUNC(void, TCPIP_CODE) lwip_rxIndication( uint8 ctrl_idx, eth_frame_type frame_type, boolean is_broadcast, const uint8* phys_addr_ptr,
                        const eth_data_type* data_ptr, uint16 len_byte ){
    struct pbuf *p;
    uint8 mac_adrs[LWIP_ETH_MAC_ADDR_SIZE];
    uint8 mac_broadcast_adrs[LWIP_ETH_MAC_ADDR_SIZE] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
    uint16 adapt_frametype;
    err_t res;
    struct netif *netif;
    lwip_netif_ctrl_type *netif_ctrl;

    p = pbuf_alloc(PBUF_RAW, len_byte + sizeof(struct eth_hdr), PBUF_RAM);
    if (p != NULL){
        if(is_broadcast == TRUE){
        MEMCPY((uint8*)&(((struct eth_hdr *)(p->payload))->dest), mac_broadcast_adrs, LWIP_ETH_MAC_ADDR_SIZE);
        }else{
#if (CONFIG_MODULE_ETHIF == 1)
            ethif_get_phys_addr(ctrl_idx,mac_adrs);
#endif
            MEMCPY((uint8*)&(((struct eth_hdr *)(p->payload))->dest), mac_adrs, LWIP_ETH_MAC_ADDR_SIZE);
        }
        MEMCPY((uint8*)&(((struct eth_hdr *)(p->payload))->src), phys_addr_ptr, LWIP_ETH_MAC_ADDR_SIZE);
        adapt_frametype =  PP_HTONS(frame_type);
        MEMCPY((uint8*)&(((struct eth_hdr *)(p->payload))->type), (void*)&adapt_frametype, LWIP_ETH_FRAMETYPE_SIZE);
        MEMCPY((uint8*)p->payload + sizeof(struct eth_hdr), data_ptr, len_byte);
        NETIF_FOREACH(netif) {
            netif_ctrl = (lwip_netif_ctrl_type *)netif->hostname;
            if (netif_ctrl!= NULL && ctrl_idx == netif_ctrl->ctrl_id) {
                break;
            }
        }
        
    if(netif != NULL){
            res = tcpip_input(p, netif);
            if((err_t)ERR_OK != res){
                (void)pbuf_free(p);
            }
    }else{
        (void)pbuf_free(p);
    }
    }else{
        /* Out of memory, Nothing to do but to through away data */
    }
}

// FUNC(void, TCPIP_CODE) LwIp_TxConfirmation(uint16 SocketId, TcpIp_Up_TxConfirmation fn)
// {
//     (void)TcpIp_Udp_TxConfirmation(SocketId, fn);
// }

static FUNC(void, TCPIP_CODE) lwip_ethernetifinit(struct netif *netif)
{
    /* set MAC hardware address length */
    netif->hwaddr_len = LWIP_ETH_MAC_ADDR_SIZE;
    netif->hwaddr[0] =  0xFFU;
    netif->hwaddr[1] =  0xFFU;
    netif->hwaddr[2] =  0xFFU;
    netif->hwaddr[3] =  0xFFU;
    netif->hwaddr[4] =  0xFFU;
    netif->hwaddr[5] =  0xFFU;

    /* maximum transfer unit */
    netif->mtu = LWIP_MTU_SIZE;

    /* device capabilities */
    /* don't set NETIF_FLAG_ETHARP if this device is not an ethernet one */
    netif->flags = NETIF_FLAG_BROADCAST | NETIF_FLAG_ETHARP | NETIF_FLAG_LINK_UP | NETIF_FLAG_IGMP;
}

/**
 * @brief  Frames Transmission function
 * @param  netif
 * @param  p
 * @retval err_t
 */
static FUNC(err_t, TCPIP_CODE) lwip_output(struct netif *netif, struct pbuf *p)
{
    err_t ret = E_OK;
#if (CONFIG_MODULE_ETHIF == 1)
    const struct pbuf *q;
    uint16 l = 0;
    uint8 *buffer;
    eth_data_type* base_address;
    uint32_t cnt;
    eth_buf_idx_type buf_index = 0;
    uint16 len_byte;
    eth_frame_type frame_type;
    BufReq_ReturnType buf_res;
    Std_ReturnType tx_res;
    uint8 ctrl_idx;
    uint8 priority;
    struct ip_hdr *iphdr;
    struct eth_hdr * ethhdr = (struct eth_hdr *)p->payload;
    lwip_netif_ctrl_type *netif_ctrl = (lwip_netif_ctrl_type *)netif->hostname;
    boolean tx_confirmation = FALSE;
    
#if ETH_PAD_SIZE
    pbuf_header(p, -ETH_PAD_SIZE); /* drop the padding word */
#endif
    ctrl_idx = netif_ctrl->ctrl_id;
    priority = netif_ctrl->priority;
    len_byte = (p->tot_len - LWIP_ETH_HEADER_SIZE);
    frame_type = PP_NTOHS(ethhdr->type);
    if (frame_type == ETHTYPE_IP) {
        iphdr = (struct ip_hdr *)((uint8 *)p->payload + LWIP_ETH_HEADER_SIZE);
        if(IPH_TOS_GET(iphdr) > 0u) {
            priority = IPH_TOS_GET(iphdr) - 1u;
            IPH_TOS_SET(iphdr, 0);
        }
    }
#if (ETHIF_ENABLE_TX_INTERRUPT == STD_OFF)
    ethif_mainfunction_tx(); // No iterations inside
#endif
    /* Note: take care to protect buffer allocation and transmit functionalities depending on the driver ,
    * Autosar spec does not say about this, and we will not protect it here */
    buf_res =  ethif_provide_tx_buffer(ctrl_idx, frame_type, priority,&buf_index,(eth_data_type **) &base_address, &len_byte);/*lint !e929 !e740 pointer access No harm */
    if((buf_res != BUFREQ_OK)){
        /* notify error and return */
        /* Try to increase the number of TX buffers in the Lower layer */
        ret = (err_t)ERR_MEM;
    }
    if (ret == E_OK) { /*lint !e737 loss of sign in promotion of ret to unsigned during comparison can be ignored */
        if (frame_type == ETHTYPE_IP) {
            iphdr = (struct ip_hdr *)((uint8 *)p->payload + LWIP_ETH_HEADER_SIZE);
            if(IPH_PROTO_GET(iphdr) == TCPIP_IPPROTO_UDP) {
                for(q = p; q != NULL; q = q->next){
                    if(q->socket_idx != -1) {
                        tcpip_buf_idx_to_socket_id[buf_index] = q->socket_idx;
                        tx_confirmation = TRUE;
                        break;
                    }
                }
            }
        }
        buffer = (uint8*)(base_address);/*lint !e923 pointer access No harm */

        /* Skip Ethernet header, ARP responses includes adding Ethernet header in the stack itself which is not easily
        * bypassed from the stack at the moment, response callback other than ARP can be moved to ASR TcpIp layer. */
        for(q = p; q != NULL; q = q->next){
            if(l == 0u){
                MEMCPY(&buffer[l], ((uint8*)q->payload + LWIP_ETH_HEADER_SIZE), (q->len - LWIP_ETH_HEADER_SIZE));/*lint !e9031 !e9016 */ /* array index is not usable */
                l = (q->len - LWIP_ETH_HEADER_SIZE);
            }else{
                MEMCPY(&buffer[l], (uint8*)q->payload, q->len);
                l = l + q->len;
            }
        }
        /* Try to send */
        cnt = 0;
        /** !req 4.2.2/SWS_TCPIP_00131 *//* Limitation in some drivers due to buffer getting free immediately when txconf is FALSE */
        tx_res = ethif_transmit(ctrl_idx,buf_index,frame_type,tx_confirmation/*txconf*/,l,ethhdr->dest.addr);
        // redundant piece of code
        while(tx_res == E_PENDING){
            if((cnt % 500) == 0){
#if (ETHIF_ENABLE_TX_INTERRUPT == STD_OFF)
                ethif_mainfunction_tx();
#endif
                tx_res = ethif_transmit(ctrl_idx,buf_index,frame_type,tx_confirmation,l,ethhdr->dest.addr);
            }
            cnt++;
            if(cnt > 1000000){
                /* timeout, notify error and return */
                ret = (err_t)ERR_TIMEOUT;
                break;
            }
        }
#if ETH_PAD_SIZE
        if (E_OK == ret ) {
            pbuf_header(p, ETH_PAD_SIZE); /* reclaim the padding word */
            /* Return SUCCESS */
        }
#endif
    }
#endif
    return ret;
}

FUNC(err_t, TCPIP_CODE) lwip_ethernetif_init(struct netif *netif) 
{
    err_t ret;
    ret = (err_t)ERR_ARG;

    if(netif != NULL){
        NETIF_INIT_SNMP(netif, snmp_ifType_ethernet_csmacd, 100000000);

        netif->name[0] = IFNAME0;
        netif->name[1] = IFNAME1;

        netif->output = etharp_output;
        netif->linkoutput = lwip_output;

        lwip_ethernetifinit(netif);
        ret = (err_t)ERR_OK;
    }

    return ret;
}
#define TCPIP_STOP_SEC_CODE
#include "tcpip_memmap.h"

#if !defined CONFIG_MODULE_TCPIP && defined CONFIG_MODULE_ETHIF && defined(ETH_IP_ADDR)
#define ETH_START_SEC_PRIVATE_BSS
#include "eth_memmap.h"
static VAR(struct netif, ETH_PRIVATE_BSS) lwip_default_netif;
#define ETH_STOP_SEC_PRIVATE_BSS
#include "eth_memmap.h"
#define TCPIP_START_SEC_CODE
#include "tcpip_memmap.h"
FUNC(void, TCPIP_CODE) lwip_add_default_netif(){
    ip4_addr_t ipaddr;
    ip4_addr_t gw;
    ip4_addr_t netmask;

    memset(&lwip_default_netif, 0, sizeof(lwip_default_netif));
    inet_aton(ETH_IP_ADDR, &ipaddr);
    inet_aton(ETH_GATEWAY, &gw);
    inet_aton(ETH_NETMASK, &netmask);
    netifapi_netif_add(&lwip_default_netif, &ipaddr, &netmask, &gw, NULL, lwip_ethernetif_init, tcpip_input);
    netifapi_netif_set_up(&lwip_default_netif);
}
#define TCPIP_STOP_SEC_CODE
#include "tcpip_memmap.h"
#endif