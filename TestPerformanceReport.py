#!/usr/bin/env python
# Author: Nikita Zakladnyi

"""
Uses a line delimited input file of domains and prints to stdout or a json file that includes:
    -DNS resolution time for the domain in seconds
    -The IP the domain resolved to
    -The time taken to establish a TCP connection to IP in seconds
    -The HTTP response code
    -The number of redirects the request went through
    -If 200 OK is received, content load time of the web site in seconds

Multi-threading for both overall website testing and for TCP time and content load testing is available in separate
 specified thread amounts.

Command line options:
    -i, --input         input file of hostname(s)
    -t, --threads       number of threads to use for host testing queue, defaults to 1 thread
    -o, --timeout       set timeout for website queue worker threads
    -j, --json          if specified, sets output to json file
    -u, --user_agent    specify a custom user-agent for requests
    -T, --tests         amount of threads each testing content load and TCP time, returns average, defaults to 1 thread

Required nonstandard modules:
    requests

Example usage:
    python3 TestPerformanceReport -i <INPUT_FILE> [OPTIONS]
"""

from optparse import OptionParser
import socket
import time
import requests
import json
import queue
import threading
import os
from statistics import mean


class TestPerformance(object):
    """
    Main object that is used by queue threads to perform the overall test using a hostname as input

    Methods:
        tcp_time():
            Gets tcp time
        get_http():
            Gets response code, number of redirects, and content load time
        time_content():
            For use by get_http() test threads to measure content load time
        test_all():
            Runs test using all methods to calculate performance output, used by queue threads
    """

    def __init__(self, hostname):
        self.hostname = hostname
        self.performance_output = {}
        self.c_header = {'host': self.hostname}  # custom header for requests
        if options.user_agent:
            self.c_header['User-agent'] = options.user_agent

        # DNS Resolution Time and IP
        dns_start = time.time()
        self.ip_address = socket.gethostbyname(self.hostname)  # DNS resolution call
        dns_end = time.time()
        self.performance_output['DNS Time'] = dns_end - dns_start
        self.performance_output['IP of Domain'] = self.ip_address

    def tcp_time(self):
        port = 80
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # connects via TCP
        # Bind call skipped, so same as calling s.bind('', 0) for IP and port
        tcp_start = time.time()
        s.connect((self.ip_address, port))
        tcp_end = time.time()
        s.close()
        self.tcp_times.append(tcp_end - tcp_start)

    def get_http(self):
        ip_to_url = 'http://{}/'.format(self.ip_address)  # IP format that's compatible with requests

        # HTTP Response Code
        host_head = requests.head(ip_to_url, headers=self.c_header, allow_redirects=True)  # retrievers headers
        host_code = host_head.status_code  # response code
        self.performance_output['HTTP Response Code'] = host_code

        # Number Redirects
        self.performance_output['Number of Redirects'] = len(host_head.history)  # redirect history

        if host_code == 200:  # if 200 OK received then get content
            # Get Content
            self.content_times = []
            self.content_threads = []
            for test_thread in range(options.test_threads):  # threads to use for testing
                r = requests.get(ip_to_url, headers=self.c_header,
                                 stream=True)  # only retrieves response headers, connection open
                content_t = threading.Thread(target=self.time_content, args=(r,))  # retrieves content
                content_t.start()
                self.content_threads.append(content_t)
            for thread in self.content_threads:  # wait until threads are finished
                thread.join()
            self.performance_output['Average Content Load Time'] = mean(self.content_times)

    def time_content(self, response):  # for use in content time threads
        content_start = time.time()
        response.content
        content_end = time.time()
        self.content_times.append(content_end - content_start)

    def test_all(self):
        # TCP times call and threading
        self.tcp_times = []
        self.tcp_threads = []
        for test_thread in range(options.test_threads):  # threads to use for testing
            tcp_t = threading.Thread(target=self.tcp_time)
            tcp_t.start()
            self.tcp_threads.append(tcp_t)
        for thread in self.tcp_threads:  # wait until threads are finished
            thread.join()
        self.performance_output['Average TCP Time'] = mean(self.tcp_times)

        # HTTP call and threading
        self.get_http()


def do_work(hostname):  # function for queue threads, different from threads for performance metrics
    o = TestPerformance(hostname)
    o.test_all()
    host_perfs[hostname] = o.performance_output


def worker():  # uses do_work() to perform
    while True:
        if options.timeout:  # checks to see if timeout used
            # if specified, exits the script if a queue thread exceeds the timeout
            try:
                if z_s + options.timeout < time.time():  # if a thread exceeds the timeout relative to script start time
                    raise TimeoutError
            except TimeoutError:
                print('TimeoutError: exceeded {}s'.format(options.timeout))
                os._exit(1)
        h = q.get()  # hostname
        if h is None:
            break
        do_work(h)
        q.task_done()


def main():
    global z_s
    z_s = time.time()  # start time of the script

    # Command Line Parser
    parser = OptionParser()
    parser.add_option("-i", "--input", dest="hostname_file",
                      help="input file of hostname(s)")
    parser.add_option("-t", "--threads", dest="num_threads", default=1,
                      help="number of threads to use for host testing queue, defaults to only one thread", type=int)
    parser.add_option("-o", "--timeout", dest="timeout", default=0,
                      help="set timeout for website queue worker threads", type=int)
    parser.add_option("-j", "--json", action="store_true", dest="json", default=False,
                      help="if specified, sets output to json file")
    parser.add_option("-u", "--user_agent", dest="user_agent", default=False,
                      help="specify a custom user-agent for requests")
    parser.add_option("-T", "--tests", dest="test_threads", default=1,
                      help="amount of threads each testing content load and TCP time, returns average, defaults 1 thread",
                      type=int)
    global options
    (options, args) = parser.parse_args()

    global host_perfs
    host_perfs = {}  # host performances
    global host_list
    host_list = []  # list of input host names

    with open(options.hostname_file) as f:  # read input hosts
        for hostname in f:
            host_list.append(hostname.rstrip())

    global q
    q = queue.Queue()  # queue for threads
    threads = []  # for keeping track of queue threads

    for i in range(options.num_threads):  # begin queue threads and start testing for each host
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    for item in host_list:
        q.put(item)

    # block until all queue threads are done
    q.join()

    # stop queue thread workers
    for i in range(options.num_threads):
        q.put(None)
    for t in threads:
        t.join()

    if options.json:
        # format input file name to output file name for json
        s_name = options.hostname_file.split('.')
        if len(s_name) > 1:
            j_name = ".".join(s_name[:-1])
        else:
            j_name = s_name[0]
        with open(j_name + '_results.json', 'w') as f:
            json.dump(host_perfs, f)
    else:
        # prints test results to stdout
        for name in host_perfs:
            print(name)
            for test in host_perfs[name]:
                print(test, ':', host_perfs[name][test])
            print()

if __name__ == '__main__':
    main()
