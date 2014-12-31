import datetime
import re
import contextlib
import os
import tempfile
import hashlib
import shutil
import subprocess
import glob
import time

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.options import define, options

import requests

from trequests import setup_session
from tornalet import tornalet

# Tell requests to use our AsyncHTTPadapter for the default
# session instance, you can also pass you own through
setup_session()


define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8000, help="run on the given port", type=int)


@contextlib.contextmanager
def make_temp_dir(url):
    dir_ = tempfile.mkdtemp('screencapper')
    yield dir_
    print "DELETING", dir_
    shutil.rmtree(dir_)


def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        if tail:
            os.mkdir(newdir)

def get_duration(filepath):
    process = subprocess.Popen(
        ['ffmpeg', '-i', filepath],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    stdout, stderr = process.communicate()
    matches = re.search(
    r"Duration:\s{1}(?P<hours>\d+?):(?P<minutes>\d+?):(?P<seconds>\d+\.\d+?),",
        stdout,
        re.DOTALL
    ).groupdict()
    hours = float(matches['hours'])
    minutes = float(matches['minutes'])
    seconds = float(matches['seconds'])

    total = 0
    total += 60 * 60 * hours
    total += 60 * minutes
    total += seconds
    return total


def _format_time(seconds):
    m = seconds / 60
    s = seconds % 60
    h = m / 60
    m = m % 60
    return '%02d:%02d:%02d' % (h, m,s)


def extract_pictures(filepath, duration, number, output):
    incr = float(duration) / number
    seconds = 0
    number = 0
    while seconds < duration:
        number += 1
        output_each = output.format(number)
        command = [
            'ffmpeg',
            '-ss',
            _format_time(seconds),
            '-y',
            '-i',
            filepath,
            '-vframes',
            '1',
            output_each,
        ]
        print ' '.join(command)
        out, err = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).communicate()
        seconds += incr
        # print out
        # print err
    # return glob.glob(os.path.join(output, '*.jpg'))


class TransformHandler(tornado.web.RequestHandler):

    # @tornado.gen.coroutine
    # def download(self, url):
    #     http_client = AsyncHTTPClient()
    #     response = yield http_client.fetch(url)
    #     return response
    #
    # @tornado.gen.coroutine
    # @tornado.web.asynchronous
    @tornalet
    def post(self):
        url = self.get_argument('url').strip()
        number = int(self.get_argument('number', 10))

        # http_client = AsyncHTTPClient()
        # request = HTTPRequest(
        #     url,
        #     connect_timeout=40.0,  # default is 20 sec
        #     request_timeout=40.0,  # default is 20 sec
        #     follow_redirects=True
        # )

        t0 = time.time()
        # response = yield http_client.fetch(request)
        response = requests.get(url)
        t1 = time.time()
        download_time = t1 - t0
        url_hash = hashlib.md5(url).hexdigest()
        with make_temp_dir(url) as temp_dir:
            file = os.path.join(
                temp_dir,
                url_hash + os.path.splitext(url)[1]
            )
            with open(file, 'wb') as f:
                size = len(response.content)
                f.write(response.content)

            duration = get_duration(file)
            # with make_temp_dir(temp_dir) as output_temp_dir
            output = '/tmp/screencap-%02d.jpg'
            # print dir(self.application)
            destination = os.path.join(
                self.application.settings['static_path'],
                'screencaps',
                datetime.datetime.utcnow().strftime('%Y/%m/%d'),
                url_hash[:10]
            )
            _mkdir(destination)
            output = os.path.join(
                destination,
                'screencap-{0:03d}.jpg'
            )
            t0 = time.time()
            extract_pictures(
                file,
                duration,
                number,
                output
            )
            t1 = time.time()
            transform_time = t1 - t0
            # response = self.download(url)
            # print response.body
            files = sorted(glob.glob(
                os.path.join(destination, 'screencap-*.jpg')
            ))
            base_url = '%s://%s' % (self.request.protocol, self.request.host)
            result = {
                'time': {
                    'download': round(download_time, 4),
                    'transform': round(transform_time, 4),
                    'total': round(download_time + transform_time, 4),
                },
                'size': size,
                'duration': duration,
                'urls': [
                    base_url + '/' + x for x in files
                ]
            }
            self.write(result)
            self.finish()


class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")
        # self.write("""<html>
        # <a href=/socktest>socktest</a><br>
        # <a href=/ajaxtest>ajaxtest</a><br>
        # </html>""")

def app():

    app_settings = dict(
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        debug=options.debug,

    )
    return tornado.web.Application([
        (r"/", HomeHandler),
        (r"/transform", TransformHandler),
    ], **app_settings)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    app().listen(options.port)
    print "Running on port", options.port
    tornado.ioloop.IOLoop.instance().start()
