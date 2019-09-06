require 'rubygems'
require 'webrick'
require 'webrick/https'
require 'openssl'
gem 'rack', '< 2.0.0'
require 'rack'
require 'socket'

require 'bootstrap.rb'
require 'pcs.rb'
require 'settings.rb'

unless defined? OpenSSL::SSL::OP_NO_TLSv1_1
  OpenSSL::SSL::OP_NO_TLSv1_1 = 268435456
end

server_name = WEBrick::Utils::getservername
$logger = configure_logger('/var/log/pcsd/pcsd.log')

def generate_cert_key_pair(server_name)
  name = "/C=US/ST=MN/L=Minneapolis/O=pcsd/OU=pcsd/CN=#{server_name}"
  ca   = OpenSSL::X509::Name.parse(name)
  key = OpenSSL::PKey::RSA.new(2048)
  crt = OpenSSL::X509::Certificate.new
  crt.version = 2
  crt.serial  = ((Time.now).to_f * 1000).to_i
  crt.subject = ca
  crt.issuer = ca
  crt.public_key = key.public_key
  crt.not_before = Time.now
  crt.not_after  = Time.now + 10 * 365 * 24 * 60 * 60 # 10 year
  crt.sign(key, OpenSSL::Digest::SHA256.new)
  return crt, key
end

def get_ssl_options()
  default_options = (
    OpenSSL::SSL::OP_NO_SSLv2 | OpenSSL::SSL::OP_NO_SSLv3 |
    OpenSSL::SSL::OP_NO_TLSv1 | OpenSSL::SSL::OP_NO_TLSv1_1
  )
  if ENV['PCSD_SSL_OPTIONS']
    options = 0
    ENV['PCSD_SSL_OPTIONS'].split(',').each { |op|
      op_cleaned = op.strip()
      begin
        if not op_cleaned.start_with?('OP_')
          raise NameError.new('options must start with OP_')
        end
        op_constant = OpenSSL::SSL.const_get(op_cleaned)
        options |= op_constant
      rescue NameError => e
        $logger.error(
          "SSL configuration error '#{e}', unknown SSL option '#{op}'"
        )
        exit
      rescue => e
        $logger.error("SSL configuration error '#{e}'")
        exit
      end
    }
    return options
  end
  return default_options
end

def run_server(server, webrick_options, secondary_addrs)
  primary_addr = webrick_options[:BindAddress]
  port = webrick_options[:Port]

  ciphers = 'DEFAULT:!RC4:!3DES:@STRENGTH'
  ciphers = ENV['PCSD_SSL_CIPHERS'] if ENV['PCSD_SSL_CIPHERS']
  # no need to validate ciphers, ssl context will validate them for us

  $logger.info("Listening on #{primary_addr} port #{port}")
  begin
    server.run(Sinatra::Application, webrick_options) { |server_instance|
      # configure ssl options
      server_instance.ssl_context.ciphers = ciphers
      if ENV['PCSD_REJECT_SSL_RENEG'] and ENV['PCSD_REJECT_SSL_RENEG'].downcase == "true" then
        # reject ssl/tls renegotiation
        negotiation_counter = Hash.new
        server_instance.ssl_context.renegotiation_cb = lambda do |ssl_socket|
          # This callback is called for every negotiation including the first
          # one for a new connection. remove all closed sockets from the
          # counter to clean it up
          negotiation_counter.delete_if { |key, val| key.io.closed? }
          # sign our socket in
          if negotiation_counter.key?(ssl_socket)
            negotiation_counter[ssl_socket] += 1
          else
            negotiation_counter[ssl_socket] = 0
          end
          # The only way to disallow the renegotiation is to raise an exception.
          if negotiation_counter[ssl_socket] > 0
            $logger.error("Client renegotiation disabled, closing connection")
            raise RuntimeError.new(
              "Client renegotiation disabled, closing connection"
            )
          end
        end
      end
      # set listening addresses
      secondary_addrs.each { |addr|
        $logger.info("Adding listener on #{addr} port #{port}")
        server_instance.listen(addr, port)
      }
      # notify systemd we are running
      if ISSYSTEMCTL
        if ENV['NOTIFY_SOCKET']
          socket_name = ENV['NOTIFY_SOCKET'].dup
          if socket_name.start_with?('@')
            # abstract namespace socket
            socket_name[0] = "\0"
          end
          $logger.info("Notifying systemd we are running (socket #{socket_name})")
          sd_socket = Socket.new(Socket::AF_UNIX, Socket::SOCK_DGRAM)
          sd_socket.connect(Socket.pack_sockaddr_un(socket_name))
          sd_socket.send('READY=1', 0)
          sd_socket.close()
        end
      end
    }
  rescue Errno::EADDRNOTAVAIL, Errno::EADDRINUSE => e
    $logger.error 'Unable to bind to specified address(es), exiting'
    $logger.error e.message
    exit 1
  rescue SocketError => e
    $logger.error e.message
    exit 1
  end
end

if not File.exists?(CRT_FILE) or not File.exists?(KEY_FILE)
  crt, key = generate_cert_key_pair(server_name)
  # File.open(path, mode, options)
  # File.open(path, mode, perm, options)
  # In order to set permissions, the method must be called with 4 arguments.
  File.open(CRT_FILE, 'w', 0600, {}) {|f| f.write(crt)}
  File.open(KEY_FILE, 'w', 0600, {}) {|f| f.write(key)}
else
  crt, key = nil, nil
  begin
    crt = File.read(CRT_FILE)
    key = File.read(KEY_FILE)
  rescue => e
    $logger.error "Unable to read certificate or key: #{e}"
  end
  crt_errors = verify_cert_key_pair(crt, key)
  if crt_errors and not crt_errors.empty?
    crt_errors.each { |err| $logger.error err }
    $logger.error "Invalid certificate and/or key, using temporary ones"
    crt, key = generate_cert_key_pair(server_name)
  end
end

dh_key_bits_default = 1024
dh_key_bits = dh_key_bits_default
if ENV['PCSD_SSL_DH_KEX_BITS']
  dh_key_bits = Integer(ENV['PCSD_SSL_DH_KEX_BITS']) rescue dh_key_bits_default
end
$logger.info "Generating #{dh_key_bits}bits long DH key..."
dh_key = OpenSSL::PKey::DH.generate(dh_key_bits)
$logger.info "DH key created"

default_bind = true
# see https://github.com/ClusterLabs/pcs/issues/51
primary_addr = if RUBY_VERSION >= '2.1' then '*' else '::' end
secondary_addrs = []
if ENV['PCSD_BIND_ADDR']
  user_addrs = ENV['PCSD_BIND_ADDR'].split(',').collect { |x| x.strip() }
  if not user_addrs.empty?
    default_bind = false
    primary_addr = user_addrs.shift()
    secondary_addrs = user_addrs
  end
end

webrick_options = {
  :Port               => ENV['PCSD_PORT'] || PCSD_DEFAULT_PORT,
  :BindAddress        => primary_addr,
  :Host               => primary_addr,
  :SSLEnable          => true,
  :SSLVerifyClient    => OpenSSL::SSL::VERIFY_NONE,
  :SSLCertificate     => OpenSSL::X509::Certificate.new(crt),
  :SSLPrivateKey      => OpenSSL::PKey::RSA.new(key),
  :SSLCertName        => [[ "CN", server_name ]],
  :SSLOptions         => get_ssl_options(),
  :SSLTmpDhCallback   => lambda {|ctx, is_export, keylen| dh_key},
}

server = ::Rack::Handler::WEBrick
trap(:INT) do
  puts "Shutting down (INT)"
  if server.instance_variable_get("@server")
    server.shutdown
  else
    exit
  end
end

trap(:TERM) do
  puts "Shutting down (TERM)"
  if server.instance_variable_get("@server")
    server.shutdown
  else
    exit
  end
end

require 'pcsd'
begin
  run_server(server, webrick_options, secondary_addrs)
rescue Errno::EAFNOSUPPORT
  if default_bind
    primary_addr = '0.0.0.0'
    webrick_options[:BindAddress] = primary_addr
    webrick_options[:Host] = primary_addr
    run_server(server, webrick_options, secondary_addrs)
  else
    raise
  end
end
