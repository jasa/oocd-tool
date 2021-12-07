#!/bin/bash
OPENSSL_CMD="/usr/bin/openssl"
RM_CMD="/usr/bin/rm"
COMMON_NAME="$1"

function show_usage {
    printf "Usage: $0 [options [parameters]]\n"
    printf "\n"
    printf "Options:\n"
    printf " -cn, Provide Common Name for the certificate\n"
    printf " -h|--help, print help section\n"

    return 0
}

case $1 in
     -cn)
         shift
         COMMON_NAME="$1"
         ;;
     --help|-h)
         show_usage
         exit 0
         ;;
     *)
        ## Use hostname as Common Name
        COMMON_NAME=`/usr/bin/hostname`
        ;;
esac


echo "Generating root CA"
$OPENSSL_CMD req -x509 -sha256 -nodes -days 1000 -newkey rsa:2048 -keyout private_ca_key.key -out ca-cert.pem -subj "/C=DK/ST=/O=oocd-tool/OU=gRPC"
if [ $? -ne 0 ] ; then
   echo "ERROR: Failed to generate self signed root CA"
   $RM_CMD $EXTFILE
   exit 1
fi

echo "Generating certificate request"
$OPENSSL_CMD req -newkey rsa:2048 -days 1000 -nodes -keyout server_key.pem -subj "/C=DK/ST=/O=oocd-tool/OU=gRPC/CN=${COMMON_NAME}" > server_req.pem
if [ $? -ne 0 ] ; then
   echo "ERROR: Failed to generate server certificate request"
   $RM_CMD $EXTFILE
   exit 1
fi

echo "Signing certificate request"
$OPENSSL_CMD x509 -req -in server_req.pem -CA ca-cert.pem -CAkey private_ca_key.key -set_serial 01 > server_cert.pem
if [ $? -ne 0 ] ; then
   echo "ERROR: Failed to sign server certificate"
fi

$RM_CMD "./private_ca_key.key"
$RM_CMD "./server_req.pem"


