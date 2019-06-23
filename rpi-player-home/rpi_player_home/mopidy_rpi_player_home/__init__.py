from __future__ import unicode_literals

import logging
import os
import re
import subprocess

from mopidy import config, ext

import tornado.web
import jinja2

__version__ = '0.1.0'

# TODO: If you need to log, use loggers named after the current Python module
logger = logging.getLogger(__name__)


template_file = os.path.join(os.path.dirname(__file__), 'index.html')


class Extension(ext.Extension):

    dist_name = 'Mopidy-RPI-Player-Home'
    ext_name = 'rpi_player_home'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        # TODO: Comment in and edit, or remove entirely
        #schema['username'] = config.String()
        #schema['password'] = config.Secret()
        return schema

    def setup(self, registry):
        registry.add('http:app', {
            'name': self.ext_name,
            'factory': app_factory,
        })


class RequestHandler(tornado.web.RequestHandler):

    def initialize(self, config):
        pass

    def get_cpu_temp(self):
        p = subprocess.Popen('vcgencmd measure_temp'.split(),
                             stdout=subprocess.PIPE)
        output, _ = p.communicate()
        if p.returncode != 0:
            return 'Unknown'
        cpu_temp = output.replace('temp=', '')
        return cpu_temp

    def get_ip_addr(self, interface):
        p = subprocess.Popen(['ifconfig', interface],
                             stdout=subprocess.PIPE)
        output, _ = p.communicate()
        m = re.search(r'inet ([\d\.]+)', output, re.MULTILINE)
        return m.group(1) if m else 'Unknown'

    def get_memstat(self):
        p = subprocess.Popen(['free', '-mh'],
                             stdout=subprocess.PIPE)
        output, _ = p.communicate()
        mem_match = re.search(r'Mem:\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)', output, re.MULTILINE)
        swap_match = re.search(r'Swap:\s+(\w+)\s+(\w+)\s+(\w+)', output, re.MULTILINE)
        if not mem_match or not swap_match:
            return None
        return {
          'mem_total': mem_match.group(1),
          'mem_used': mem_match.group(2),
          'mem_free': mem_match.group(3),
          'mem_shared': mem_match.group(4),
          'mem_buff_cache': mem_match.group(5),
          'mem_buff_available': mem_match.group(6),
          'swap_total': swap_match.group(1),
          'swap_used': swap_match.group(2),
          'swap_free': swap_match.group(3),
        }

    def get(self):
        templateLoader = jinja2.FileSystemLoader(searchpath="/")
        templateEnv = jinja2.Environment(loader=templateLoader)
        template = templateEnv.get_template(template_file)

        memstat = self.get_memstat()

        templateVars = {
            'title': 'Home',
            'cpu_temp': self.get_cpu_temp(),
            'wan_ip_addr': self.get_ip_addr('wlan0'),
            'lan_ip_addr': self.get_ip_addr('eth0'),
            'mem': '{} total, {} free, {} used, {} buff/cache'
                .format(memstat['mem_total'], memstat['mem_free'],
                        memstat['mem_used'], memstat['mem_buff_cache']) \
                if memstat else 'Unknown',
            'swap': '{} total, {} free, {} used'
                .format(memstat['swap_total'], memstat['swap_free'],
                        memstat['swap_used']) \
                if memstat else 'Unknown',
        }
        self.write(template.render(templateVars))


def app_factory(config, core):
    from mopidy.http.handlers import StaticFileHandler
    path = os.path.join(os.path.dirname(__file__), 'static')
    return [
        ('/',             RequestHandler,    {'config': config}),
        (r'/static/(.*)', StaticFileHandler, {'path': path})
    ]
