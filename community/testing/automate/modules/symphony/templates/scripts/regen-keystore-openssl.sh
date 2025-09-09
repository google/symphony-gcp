#!/bin/bash

configure_egosh_ssl () {
    
    # ========================== CA and Server (self-signed) certificate regeneration code ==========================
    #
    # This script regenerates the CA certificate and key, server certificate and key, and transform these into 
    # the keystore format used by Symphony.
    # 
    # TODO: Add a way to change the password :-/
    # 
    # ===============================================================================================================

    # ============== Input variables ===============

    # Fail if any commands fail...
    set -eo pipefail

    # export COMMON_NAME=$(hostname -d) # common host name
    # unique host name, e.g. host1.example.com ; host2.example.com
    # export SUBJECT_ALTERNATIVE_NAMES="DNS:symphony-mgmt-0.us-central1-a.c.symphony-gcp-host-factory.internal,DNS:symphony-mgmt-1.us-central1-a.c.symphony-gcp-host-factory.internal" # unique host name

    if [ -z $EGO_TOP ]; then
        echo "EGO_TOP variable is not set. Exiting."
        return 1
    fi

    if [ -z $COMMON_NAME ]; then
        echo "COMMON_NAME variable is not set. Exiting."
        return 1
    fi

    if [ -z $SUBJECT_ALTERNATIVE_NAMES ]; then
        echo "SUBJECT_ALTERNATIVE_NAMES variable is not set. Exiting."
        return 1
    fi

    # ============== Auxiliary variables ==============


    STORE_PASS=Liberty # TODO: Find a way to better change this...

    KEYSTORE_FOLDER=$EGO_TOP/wlp/usr/shared/resources/security # keystore path
    KEYSTORE_FILE=serverKeyStore.jks # DO NOT CHANGE, keystore default name
    TRUST_KEYSTORE_FILE=serverTrustStore.jks # DO NOT CHANGE, trust keystore default name

    KEYSTORE_FILE_OPEN=serverKeyStore.p12 # p12 keystore name
    TRUST_KEYSTORE_FILE_OPEN=serverTrustStore.p12 # p12 server keystore name

    KEYTOOL=$EGO_TOP/jre/8.0.6.36/linux-x86_64/bin/keytool # keytool path

    CA_KEY_FILE=cacert.key # Certificate authority key file to be generated
    CA_CERT_FILE=cacert.pem # Certificate authority certificate file to be generated
    SRV_KEY_FILE=servercert.key # Server key file to be generated
    SRV_CSR_FILE=srvcertreq.csr # Server certificate signing request to be generated
    SRV_CERT_FILE=servercertcasigned.pem # Server certificate to be created
    CERT_CONF_FILE=openssl-san.cnf # Certificate configuration file


    # ============== Certificate Authority / CA ==============

    echo "Regenerating certificates to $KEYSTORE_FOLDER"

    echo "Generating root CA key..."
    openssl genrsa -out $KEYSTORE_FOLDER/$CA_KEY_FILE  4096

    echo "Generating root certificate..."
    openssl req -x509 -new -nodes \
        -key $KEYSTORE_FOLDER/$CA_KEY_FILE -sha256 -days 1024 \
        -out $KEYSTORE_FOLDER/$CA_CERT_FILE -subj="/CN=Leet Authority" -outform PEM

    # ============== Server ==============

    echo "Generating server key..."
    openssl genrsa -out $KEYSTORE_FOLDER/$SRV_KEY_FILE 2048

    echo "Generating configuration file..."
    cat <<EOF > $KEYSTORE_FOLDER/$CERT_CONF_FILE
[req]
distinguished_name=req
req_extensions=san
[req_distinguished_name]
[san]
subjectAltName=$SUBJECT_ALTERNATIVE_NAMES
EOF

    echo "Generating certificate signing request..."
    openssl req -new -sha256 -key $KEYSTORE_FOLDER/$SRV_KEY_FILE \
        -subj "/CN=*.$COMMON_NAME/O=Leet Org./C=BR/" \
        -config $KEYSTORE_FOLDER/$CERT_CONF_FILE \
        -out $KEYSTORE_FOLDER/$SRV_CSR_FILE

    # Inspect certificate signing request...
    # openssl req -noout -text -in $SRV_CSR_FILE

    echo "Signing certificate with root key..."
    openssl x509 -req \
        -in $KEYSTORE_FOLDER/$SRV_CSR_FILE \
        -CA $KEYSTORE_FOLDER/$CA_CERT_FILE \
        -CAkey $KEYSTORE_FOLDER/$CA_KEY_FILE \
        -CAcreateserial \
        -out $KEYSTORE_FOLDER/$SRV_CERT_FILE \
        -days 500 -sha256 -outform PEM \
        -extfile $KEYSTORE_FOLDER/$CERT_CONF_FILE \
        -extensions san

    # Inspect certificate signing request...
    # openssl x509 -noout -text -in $KEYSTORE_FOLDER/$SRV_CERT_FILE


    # ============== Update keystore ==============

    # Backup keystore
    if [ -f $KEYSTORE_FOLDER/$KEYSTORE_FILE ]; then
        echo "Backing up old keystore..."
        mv $KEYSTORE_FOLDER/$KEYSTORE_FILE $KEYSTORE_FOLDER/$KEYSTORE_FILE.bkp
    else
        echo "Old keystore not found, skipping backup..."
    fi

    echo "Generating pkcs12 keystore"
    openssl pkcs12 -export \
        -in $KEYSTORE_FOLDER/$SRV_CERT_FILE \
        -inkey $KEYSTORE_FOLDER/$SRV_KEY_FILE \
        -out $KEYSTORE_FOLDER/$KEYSTORE_FILE_OPEN \
        -name srvalias \
        -passout pass:$STORE_PASS
        # -certfile $KEYSTORE_FOLDER/$CA_CERT_FILE \

    echo "Converting keystore using keytool..."
    $KEYTOOL -importkeystore \
        -noprompt \
        -srckeystore $KEYSTORE_FOLDER/$KEYSTORE_FILE_OPEN \
        -destkeystore $KEYSTORE_FOLDER/$KEYSTORE_FILE \
        -srcstoretype pkcs12 \
        -srcstorepass $STORE_PASS \
        -deststorepass $STORE_PASS \
        -alias srvalias

    # Inspect keystore...
    # $KEYTOOL -v -list -keystore $KEYSTORE_FOLDER/$KEYSTORE_FILE -storepass $STORE_PASS
    # 

    # ============== Update serverTrustStore ==============
    # Required because it is a self-signed certificate

    if [ -f $KEYSTORE_FOLDER/$TRUST_KEYSTORE_FILE ]; then
        echo "Backing up old serverTrustStore..."
        mv $KEYSTORE_FOLDER/$TRUST_KEYSTORE_FILE $KEYSTORE_FOLDER/$TRUST_KEYSTORE_FILE.bkp
    else
        echo "Old serverTrustStore not found, skipping backup..."
    fi

    echo "Generating pkcs12 serverTrustStore..."
    openssl pkcs12 -export \
        -in $KEYSTORE_FOLDER/$CA_CERT_FILE \
        -inkey $KEYSTORE_FOLDER/$CA_KEY_FILE \
        -out $KEYSTORE_FOLDER/$TRUST_KEYSTORE_FILE_OPEN \
        -name srvalias \
        -passout pass:$STORE_PASS

    echo "Converting serverTrustStore using keytool..."
    $KEYTOOL -importkeystore \
        -noprompt \
        -destkeystore $KEYSTORE_FOLDER/$TRUST_KEYSTORE_FILE \
        -srckeystore $KEYSTORE_FOLDER/$TRUST_KEYSTORE_FILE_OPEN \
        -srcstoretype pkcs12 \
        -alias srvalias \
        -srcstorepass $STORE_PASS \
        -deststorepass  $STORE_PASS

    # Inspect keystore...
    # $KEYTOOL -v -list -keystore $KEYSTORE_FOLDER/$TRUST_KEYSTORE_FILE -storepass $STORE_PASS


    # export URL=symphony-mgmt--0.us-central1-a.c.symphony-gcp-host-factory.internal
    # export CERT_PATH=${EGO_TOP}/wlp/usr/shared/resources/security/cacert.pem

    # curl --cacert $CERT_PATH --resolve $URL:8543:10.128.15.198 https://$URL:8543

}
