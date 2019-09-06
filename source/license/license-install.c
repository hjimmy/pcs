#include <stdlib.h>
#include <stdio.h>
#include <string.h>

int main(int argc,char *argv[])
{
	if (argc <= 1){
           printf("Please input license file path!\n");
	   return 1;
        }
        char str[200] = "cp ";
        strcat(str, argv[1]);
	strcat(str, " /etc/corosync/.license.dat");
	system(str);
        return 0;
}
