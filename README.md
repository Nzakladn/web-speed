# Website Speed Test Tool

A python3 command-line script for testing speed of a list websites

## Description

Uses a line delimited input file of domains and prints to stdout or a json file that includes:
    -DNS resolution time for the domain in seconds
    -The IP the domain resolved to
    -The time taken to establish a TCP connection to IP in seconds
    -The HTTP response code
    -The number of redirects the request went through
    -If 200 OK is received, content load time of the web site in seconds

Multi-threading for both overall website testing and for TCP time and content load testing is available in separate
 specified thread amounts.

### Required Module

requests

### Command Line Options

-i, --input         input file of hostname(s)
-t, --threads       number of threads to use for host testing queue, defaults to 1 thread
-o, --timeout       set timeout for website queue worker threads
-j, --json          if specified, sets output to json file
-u, --user_agent    specify a custom user-agent for requests
-T, --tests         amount of threads each testing content load and TCP time, returns average, defaults to 1 thread

### Example Usage

```
python3 webspeed.py -i <INPUT_FILE> [OPTIONS]
```
