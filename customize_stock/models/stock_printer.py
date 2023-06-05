# preparation

# curently in progress

_logger.info(
    'Sending job to CUPS printer %s on %s'
    % (self.system_name, self.server_id.address))
options = self.print_options(report=report, **print_opts)
options_str = ""
for option, value in options.items():
    options_str += "-o %s=%s" % (option, value,)
_logger.info("Cmd: %s", 'lp -h %s:%s -d %s %s %s' %
             (self.server_id.address,
              self.server_id.port,
              self.system_name,
              options_str,
              file_name))
os.system('lp -h %s:%s -d %s %s %s' %
          (self.server_id.address,
           self.server_id.port,
           self.system_name,
           options_str,
           file_name))
_logger.info("Printing job: '%s' on %s" % (
    file_name,
    self.server_id.address,
))