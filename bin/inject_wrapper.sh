#!/bin/bash
#
#  Copyright 2015 CityGrid Media, LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
PIP_DL_LOCATION="/media/dists/"

function usage {
cat << EOF
 
usage:$0 options
 
Twonicorn artifact injection wrapper.
 
OPTIONS:
       -h      Show this messages
       -b      The branch/tag that built the artifact.
       -d      The deployment id in the twonicorn DB.
       -e      Environment. Choices are dev, or qat. You cannot inject
               directly to prd, as prd artifacts are promoted. This
               option is required for non-confs.
       -s      Suffix. Used for jar files to find the right one.
       -t      Type of artifact. Valid choices are:
                  svn_conf
                  gerrit_conf
                  war
                  jar
       -v      Verbose output. 
 
EOF
}

function check_conf_dir() {

   # Make sure the conf subdir exists,otherwise abort
   if [ ! -d ${WORKSPACE}/conf ] ; then
      echo "conf dir not found in the workspace, aborting."
      exit 2
   fi

}

function svn_conf() {

   check_conf_dir

   LOCATION=${SVN_URL//https:\/\/svn.prod.cs/}

   if [ -z ${LOCATION} ] ; then
      echo "Unable to determine artifact LOCATION from SVN_URL, aborting."
      exit 1
   fi
   
   # environment is really only needed for non-confs. Need to find a nicer way to deal with this.
   CMD="/app/twonicorn/bin/inject.py ${VERBOSE} --deploy-id ${DEPLOYMENT_ID} --repo-id 2 --environment dev --location ${LOCATION} --revision ${SVN_REVISION} --user ${BUILD_USER_ID}"
   echo -e "\nExecuting: ${CMD}\n"
   ${CMD}
}

function gerrit_conf() {

   check_conf_dir

   LOCATION=${GIT_URL//ssh:\/\/git_ci@gerrit.ctgrd.com\:29418/}

   if [ -z ${LOCATION} ] ; then
      echo "Unable to determine artifact LOCATION from GIT_URL, aborting."
      exit 1
   fi

   # environment is really only needed for non-confs. Need to find a nicer way to deal with this.
   CMD="/app/twonicorn/bin/inject.py ${VERBOSE} --deploy-id ${DEPLOYMENT_ID} --repo-id 3 --environment dev --location ${LOCATION} --revision ${GIT_COMMIT} --user ${BUILD_USER_ID}"
   echo -e "\nExecuting: ${CMD}\n"
   ${CMD}
}

function war() {

   JENKINS_LOG_FILE="${JENKINS_HOME}/jobs/${JOB_NAME}/builds/${BUILD_NUMBER}/log"
   echo -e "\nBUILD_URL is: ${BUILD_URL}"
   echo "LOG_FILE is: ${JENKINS_LOG_FILE}"

   while [ -z ${ARTIFACT} ] ; do
     sleep 1
     ARTIFACT=`grep -a -e "Uploaded\: .*.war" -o ${JENKINS_LOG_FILE} | awk '{print $2}' | head -1`
     LOCATION=${ARTIFACT//http:\/\/nexus.prod.cs:8081/}
     echo "ARTIFACT is: ${ARTIFACT}"
     echo -e "LOCATION is: ${LOCATION}\n"
   done
   
   regex='.*.war$'

   if [ ! -z "$SVN_REVISION" ] ; then
      REVISION=${SVN_REVISION}
   elif [ ! -z "$GIT_COMMIT" ] ; then
      REVISION=${GIT_COMMIT}
   else
      echo "Unable to find SVN_REVISION or GIT_COMMIT"
      exit 1
   fi

   CMD="/app/twonicorn/bin/inject.py ${VERBOSE} --deploy-id ${DEPLOYMENT_ID} --repo-id 1 --environment ${ENV} --location ${LOCATION} --branch=${BRANCH} --revision ${REVISION} --user ${BUILD_USER_ID}"
   
   if [[ $ARTIFACT =~ $regex ]] ; then
      echo -e "\nExecuting: ${CMD}\n"
      ${CMD}
   else
     echo -e "\nERROR: There is a problem determining the artifact\n"
     exit 1
   fi

}

function tar() {

   JENKINS_LOG_FILE="${JENKINS_HOME}/jobs/${JOB_NAME}/builds/${BUILD_NUMBER}/log"
   echo -e "\nBUILD_URL is: ${BUILD_URL}"
   echo "LOG_FILE is: ${JENKINS_LOG_FILE}"

   while [ -z ${ARTIFACT} ] ; do
     sleep 1
     ARTIFACT=`grep -a -e "Uploaded\: .*.tar.gz" -o ${JENKINS_LOG_FILE} | awk '{print $2}' | head -1`
     LOCATION=${ARTIFACT//http:\/\/nexus.prod.cs:8081/}
     echo "ARTIFACT is: ${ARTIFACT}"
     echo -e "LOCATION is: ${LOCATION}\n"
   done

   regex='.*.tar.gz$'

   if [ ! -z "$SVN_REVISION" ] ; then
      REVISION=${SVN_REVISION}
   elif [ ! -z "$GIT_COMMIT" ] ; then
      REVISION=${GIT_COMMIT}
   else
      echo "Unable to find SVN_REVISION or GIT_COMMIT"
      exit 1
   fi

   CMD="/app/twonicorn/bin/inject.py ${VERBOSE} --deploy-id ${DEPLOYMENT_ID} --repo-id 1 --environment ${ENV} --location ${LOCATION} --branch=${BRANCH} --revision ${REVISION} --user ${BUILD_USER_ID}"

   if [[ $ARTIFACT =~ $regex ]] ; then
      echo -e "\nExecuting: ${CMD}\n"
      ${CMD}
   else
     echo -e "\nERROR: There is a problem determining the artifact\n"
     exit 1
   fi

}

function jar() {

   JENKINS_LOG_FILE="${JENKINS_HOME}/jobs/${JOB_NAME}/builds/${BUILD_NUMBER}/log"
   echo -e "\nBUILD_URL is: ${BUILD_URL}"
   echo "LOG_FILE is: ${JENKINS_LOG_FILE}"

   while [ -z ${ARTIFACT} ] ; do
     sleep 1
#     JAR=`ls -1 ${JENKINS_HOME}/jobs/${JOB_NAME}/builds/${BUILD_NUMBER}/archive/target/`
     ARTIFACT=`grep -a "Uploaded\: .*${SUFFIX}" -o ${JENKINS_LOG_FILE} | awk '{print $2}'`
     LOCATION=${ARTIFACT//http:\/\/nexus.prod.cs:8081/}
     echo "ARTIFACT is: ${ARTIFACT}"
     echo -e "LOCATION is: ${LOCATION}\n"
   done

   regex='.*.jar$'

   if [ ! -z "$SVN_REVISION" ] ; then
      REVISION=${SVN_REVISION}
   elif [ ! -z "$GIT_COMMIT" ] ; then
      REVISION=${GIT_COMMIT}
   else
      echo "Unable to find SVN_REVISION or GIT_COMMIT"
      exit 1
   fi

   CMD="/app/twonicorn/bin/inject.py ${VERBOSE} --deploy-id ${DEPLOYMENT_ID} --repo-id 1 --environment ${ENV} --location ${LOCATION} --branch=${BRANCH} --revision ${REVISION} --user ${BUILD_USER_ID}"

   if [[ $ARTIFACT =~ $regex ]] ; then
      echo -e "\nExecuting: ${CMD}\n"
      ${CMD}
   else
     echo -e "\nERROR: There is a problem determining the artifact\n"
     exit 1
   fi

}

function python() {

   JENKINS_LOG_FILE="${JENKINS_HOME}/jobs/${JOB_NAME}/builds/${BUILD_NUMBER}/log"
   echo -e "\nBUILD_URL is: ${BUILD_URL}"
   echo "LOG_FILE is: ${JENKINS_LOG_FILE}"

   while [ -z ${ARTIFACT} ] ; do
     sleep 1
     ARTIFACT=`grep -a -e "Submitting dist\/.*.tar.gz" -o ${JENKINS_LOG_FILE} | awk -F\/ '{print $2}' | head -1`
     LOCATION=${PIP_DL_LOCATION}${ARTIFACT}
     echo "ARTIFACT is: ${ARTIFACT}"
     echo -e "LOCATION is: ${LOCATION}\n"
   done

   regex='.*.tar.gz$'

   if [ ! -z "$SVN_REVISION" ] ; then
      REVISION=${SVN_REVISION}
   elif [ ! -z "$GIT_COMMIT" ] ; then
      REVISION=${GIT_COMMIT}
   else
      echo "Unable to find SVN_REVISION or GIT_COMMIT"
      exit 1
   fi

   CMD="/app/twonicorn/bin/inject.py ${VERBOSE} --deploy-id ${DEPLOYMENT_ID} --repo-id 4 --environment ${ENV} --location ${LOCATION} --branch=${BRANCH} --revision ${REVISION} --user ${BUILD_USER_ID}"

   if [[ $ARTIFACT =~ $regex ]] ; then
      echo -e "\nExecuting: ${CMD}\n"
      ${CMD}
   else
     echo -e "\nERROR: There is a problem determining the artifact\n"
     exit 1
   fi

}

while getopts "hvb:d:e:s:t:" OPTION; do
    case $OPTION in
        h)
            usage
            exit 1
            ;;
        b)
            BRANCH=$OPTARG
            ;;
        d)
            DEPLOYMENT_ID=$OPTARG
            ;;
        e)
            ENV=$OPTARG
            ;;
        s)
            SUFFIX=$OPTARG
            ;;
        t)
            TYPE=$OPTARG
            ;;
        v)
            VERBOSE='-v'
            ;;
        ?)
            usage
            exit 1
            ;;
    esac
done

# For some reason builds triggered with poll scm don't set this var to csweb.
if [ -z "$BUILD_USER_ID" ] ; then
   BUILD_USER_ID="csweb"
fi

# Loic's AD name strikes again.
BUILD_USER_ID=${BUILD_USER_ID//\'/}

# Prevent from running this script for the prod env
if [[ "$ENV" == "dev" ]] || [[ "$ENV" == "qat" ]] || [[ $TYPE = *_conf ]]; then
  $TYPE
else
  echo "Valid environment choices are dev or qat only."
  exit 2
fi
