#!/usr/bin/python
import os
import sys
import datetime
import shutil
import smtplib
from os import path

try:
    from ipaddress import IPv4Network, IPv4Address
except ImportError:
    print("\nPython Module 'ipaddress' doesn't seems to be exist, exiting..\n")
    sys.exit(100)

# Variables declaration part
# DC Specific Variables
DC = '""'   # Mention DNS Search domain name (Ex: us4.zoho.com) inside double-quotes
dcShort = ""  # Mention Dc Prefix in CAPITAL (Ex: US4)
"""Uncomment below if condition with relevant details to support small DCs (i.e arattai or charm) within deployments
if (len(sys.argv) - 1) == 2:
	if sys.argv[2] == "arattai":    #mention arattai or charm ,etc..
		DC = '"in2arattai.zoho.in"'
		dcShort = "IN2 Arattai"  """
senderMail = "dhcp-noreply@zoho.com|eu|in|com.au"       # Region specific source mail address
nameserverList = ''     # Mention list of name servers with comma separated
ntpserverList = nameserverList  # + ",<additional_ips_if_any>"      # List of NTP servers are taken from Name servers list + Mention additional NTP Servers if required

# Common Variables - DO NOT CHANGE
dhcpConf = "/etc/dhcp/dhcpd.conf"
leaseFile = "/var/lib/dhcpd/dhcpd.leases"
backupDir = "/root/dhcp-conf-backup/"
smtpServer = "smtp"
receiverMail = "zorro-l3-alerts@zohocorp.com"
timenow = datetime.datetime.now()
servstat = ('systemctl is-active --quiet dhcpd')
leasetest = ("dhcpd -T | grep -q 'Corrupt lease file'")
configtest = ("dhcpd -q -t")


def showerr(text):
    print("\n" + text + "\n")
    sys.exit(127)


def isfileExist(pathcheck):
    out = (str(path.exists(pathcheck)))
    return out


def execCmd(cmd):
    cmdout = os.system(cmd)
    return cmdout

def showusage():
    showerr("Usage: dhcptool < add_scope | mod_scope | del_scope | clear_lease | update_lease >\
             \n\nAction Type Definitions:\n\tadd_scope: Add new IP range to DHCP Conf\
             \n\tmod_scope: Modify an existing IP range from DHCP Conf. Option is not supported as of now\
             \n\tdel_scope: Delete the IP range from DHCP Conf. Option is not supported as of now\
             \n\tclear_lease: Clear unused IPs from DHCP Leases. Option is not supported as of now\
             \n\tupdate_lease: Update IP and MAC on DHCP Leases. Option is not supported as of now\
             \n\nNOTE: Run \"dhcptool <action_type> arattai\" to execute certain actions on Arattai Setup")

def getConfirmation():
    quest = input("\nIP Validation checks are PASSED. Confirm to proceed[yes/no]: ")
    yans = ['yes', 'Yes', 'YES', 'y']
    if quest not in yans:
        showerr("Script is Aborted. Exiting..")
    else:
        return


def preChecks():
    """Pre checks before running the script"""
    # Checking whether Dhcp Daemon is running or not
    if execCmd(servstat) != 0:
        showerr("Error: DHCPD service is not running. Exiting..")
    # Checking whether Dhcp Server Conf file is exist or not
    elif isfileExist(dhcpConf) == "False":
        showerr("Error: Oops.. DHCP Server Conf is NOT available :( Exiting..")
    # Checking whether Dhcp Server Conf file is exist or not
    elif isfileExist(leaseFile) == "False":
        showerr("Error: Oops.. DHCP Leases File is NOT available :( Exiting..")
    # Perform Config Tests
    elif execCmd(configtest) != 0:
        showerr("\nError: Existing DHCP Configuration file has Syntax errors. Please check manually and fix it..")
    elif execCmd(leasetest) == 0:
        showerr("Error: Existing DHCP Lease file has Syntax errors. Please check manually and fix it..")
    else:
        pass
    return


def getData():
    print("\nPlease enter new VLAN details for " + dcShort + "..\n")
    # Get input values
    global name, net, startip, endip, nameserver, ntpserver
    name = input("Enter VLAN Name: ")
    net = input("Subnet with Prefix eg:-10.0.0.0 /24: ")
    startip = input("Enter Start IP Address: ")
    endip = input("Enter End IP Address: ")
    nameserver = input("DNS Servers[comma separated][ENTER to Default]: ")
    ntpserver = input("NTP Servers[comma separated][ENTER to Default]: ")
    # set default nameserver & ntpserver values if input was empty
    if not nameserver:
        nameserver = nameserverList
    if not ntpserver:
        ntpserver = ntpserverList
    return


def cidrValidation():
    """Validating Subnet and Netmask values"""
    if not net:
        showerr("Error: Aborting script due to empty Subnet is given. Exiting..")
    else:
        global network, subnet, netmask, bcast
        try:
            network = IPv4Network(net)
        except ValueError:
            showerr("Error: Aborting script due to INVALID Subnet is given..")
        # get CIDR/Netmask & other stuffs
        subnet, cidr, netmask, bcast = str(network.network_address), str(network.prefixlen), str(network.netmask), str(
            network.broadcast_address)
        subnetCheck = ("grep -w -q " + subnet + " " + dhcpConf)
        if cidr < '16' or cidr > '26':
            showerr("Error: Entered prefix /" + cidr + " is NOT a recommended value. Exiting..")
        elif execCmd(subnetCheck) == 0:  # check if entered subnet is already exist in conf
            showerr("Error: Given VLAN " + subnet + " already exist on DHCP Conf. Exiting..")
    return


def ipaddrValidation(ipList):
    """IP VALIDATION - MAIN PART"""
    for ip in ipList[1:-2]:
        try:
            ip_addr = IPv4Address(ip)
        except ValueError:
            showerr("Error: Aborting script due to Empty IP/ INVALID IP is given..")
        if bcast == ip:
            showerr("Error: Do NOT enter Broadcast address [" + bcast + "] of the subnet. Script Exiting..")
        elif ip_addr.is_loopback:
            showerr("Error: Detected Loopback address 127.x.x.x. Script Exiting..")
        elif ip_addr.is_link_local:
            showerr("Error: Detected Link Local Address 169.254.169.x. Script Exiting..")
        elif ip_addr.is_global:
            showerr("Error: Detected Public IP address. Script Exiting..")
        elif ip_addr.is_multicast:
            showerr("Error: Detected MultiCast IP address. Script Exiting..")
        elif ip_addr not in network:
            showerr("Error: IP " + ip + " is NOT part of the given subnet range. Exiting..")
    return


def pingGateway():
    """Ping check for Gateway IP"""
    gwPing = ("ping -c2 " + ans[5] + " | grep -q '100% packet loss'")
    if execCmd(gwPing) == 0:
        showerr("Error: Gateway IP " + ans[5] + " for this subnet is not reachable. Exiting..")
    return


def copyFiles(src, dst):
    """Copy Files"""
    try:
        shutil.copy(src, dst)
    except:
        showerr("Error: Failed to backup conf and lease files. Please check manually..")
    return


def saveBackupTo(dir):
    """Backing up DHCP server conf and Lease file"""
    if isfileExist(dir) == "False":
        try:
            os.mkdir(dir)
        except:
            showerr("Error: Permission denied to create the backup directory " + dir)

    bigFiles = [dhcpConf, leaseFile]
    for cnf in bigFiles:
        cf = cnf.split('/')[-1]
        target = dir + cf + "-" + str(timenow)
        copyFiles(cnf, target)


def updateConf():
    """UPDATE DHCP SERVER CONFIGURATION"""
    try:
        dhServConf = open(dhcpConf, "a")
        dhServConf.write(
            "\n#IP Pool for " + ans[0] + "\nsubnet " + ans[1] + " netmask " + ans[4] + " {\n  range " + ans[2] + " " + ans[3] + " ;" + "\n  option domain-name " + DC + " ;\n  option domain-name-servers " + nameserver + " ;\n  option ntp-servers " + ntpserver + " ;\n  default-lease-time -1 ;\n  max-lease-time -1 ;\n  option routers " + ans[5] + " ;\n}\n")
        dhServConf.close()
    except:
        showerr("Error: Permission denied to update dhcpd.conf file. Are you root ? ")
    return


def showMsg():
    """Show details"""
    global showResult
    showResult = "\n\nNew Scope is added to DHCP Server. Please find the below details,\n" + "\nVLAN Name: " + ans[0] + "\nSubnet: " + ans[1] + "\nNetmask: " + ans[4] + "\nStart IP: " + ans[2] + "\nEnd IP: " + ans[3] + "\nDNS Server(s): " + nameserver + "\nNTP Server(s): " + ntpserver + "\nGateway: " + ans[5] + "\n\n"
    print("\nSuccessfully updated the range in DHCP server conf and restarted the service !!!" + showResult)
    return


def sendReport():
    """Send E-Mail Report to team with the information about modifications"""
    SUB = dcShort + " - DHCP - Scope Added"
    TXT = "Dear Team," + showResult + "Generated By,\n" + dcShort + " - DHCP\n" + str(timenow)
    message = 'To: {}\nSubject: {}\n\n{}'.format(receiverMail, SUB, TXT)
    try:
        server=smtplib.SMTP(smtpServer)
        server.sendmail(senderMail, receiverMail, message)
        server.quit()
    except:
        print("\nWarning: Sending e-mail report to team has failed due to SMTP server connectivity issues..\n")
    return


def main():
    """Main Function"""
    global ans
    preChecks()
    getData()
    cidrValidation()
    # Set first IP as gateway
    gateway = str(network[1])
    # Store the input values in a list
    ans = [name, subnet, startip, endip, netmask, gateway]
    ipaddrValidation(ans)
    pingGateway()
    getConfirmation()
    saveBackupTo(backupDir)
    ##########################
    updateConf()
    ##########################
    if execCmd(configtest) == 0:
        servrestart = ("systemctl restart dhcpd")
        if execCmd(servrestart) == 0:
            showMsg()
            sendReport()
        else:
            showerr("Error: DHCP Conf is Updated but FAILED to restart the service. Please check manually..")
    else:
        showerr("Error: DHCP Conf is Updated but it has met with Syntax errors. Please check manually..")
    return


# Checking whether script is executed with one argument
if (len(sys.argv) - 1) == 0:
    showusage()
else:
    arglist = ['add_scope', 'mod_scope', 'del_scope', 'clear_lease', 'update_lease']
    if sys.argv[1] in arglist:
        if sys.argv[1] == "add_scope":
            main()
        else:
            showerr("DHCP Operation tool will support " + sys.argv[1] + " feature soon..")
    else:
        showusage()
# Checks to be added
# Check Wrote Value from /var/log/messages
# 
# Lease file config test output is getting printed and also more valid errors to be added
# dhcpd -T -lf /tmp/dhcpd.leases &> /tmp/dhcptool.out && egrep -q 'Corrupt lease file|unexpected end of file' /tmp/dhcptool.out
