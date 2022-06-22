#!/bin/bash
# Configuration of the HTTPDNS accuracy evaluator
# httpdns_accuracy Copyright (C) 2017  Aliyun inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
DOMAINS_FILE_PATH='./domains.txt'

if ! [ -x "$(command -v dig)" ]; then
  echo 'Error:dig is not installed.' >&2
  exit 1
fi

if [ $# -eq 1 ]; then
  DOMAINS_FILE_PATH=$1
fi

if ! [ -f "$DOMAINS_FILE_PATH" ]; then
  echo "Error:domain file $DOMAINS_FILE_PATH not exist" >&2
  exit 1
fi

for domain in $(cat "$DOMAINS_FILE_PATH"); do
  while [ "$domain" ]; do
    cname=$domain
    domain=$(dig "$domain" CNAME +short)
  done
  ns=$(dig "$cname" +trace | grep 'Received' | tail -1 | grep -Eo "\((.*)\)" | grep -Eo "([0-9a-zA-Z.-]+)")
  domain_configs="\t("\'"${cname%.}"\'","\'"${ns%.}"\'"),\n$domain_configs"
done
domain_configs="HOSTS = (\n${domain_configs%,*}\n)"

echo -e $domain_configs
