import datetime
import commands
import os
import base64
license_file = "/etc/corosync/.license.dat"

def create_license():
    if os.path.exists(license_file):
        return 0
    else:
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=30)
        n_days = now + delta
        expire_time = n_days.strftime('%Y-%m-%d %H:%M:%S')
        s1 = base64.encodestring(expire_time)
        f = open(license_file, 'w')
        f.write(s1)
        f.close()
        return 1


def check_license():
    if os.path.exists(license_file):
        with open(license_file, 'r') as f:
           expire_time_en = f.read()
           f.close()
           s2 = base64.decodestring(expire_time_en)
           now = datetime.datetime.now()
           now_str = now.strftime('%Y-%m-%d %H:%M:%S')
           now_time = datetime.datetime.strptime(now_str, '%Y-%m-%d %H:%M:%S')
           expire_time = datetime.datetime.strptime(s2, '%Y-%m-%d %H:%M:%S')
           delta = expire_time - now_time
           left_day = delta.days
           if left_day >= 0:
               return left_day
           else:
               return -1

if __name__ == '__main__':
    create_license()
    if check_license() >= 0:
       status, output = commands.getstatusoutput("/usr/sbin/pacemakerd -f")
    else:
       print "The license has expired, please contact technical support!"
