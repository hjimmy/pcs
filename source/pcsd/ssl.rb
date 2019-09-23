require 'rubygems'
require 'webrick'
require 'webrick/https'
require 'openssl'
require 'rack'

require 'bootstrap.rb'
require 'pcs.rb'

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
    OpenSSL::SSL::OP_NO_TLSv1 | 268435456
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

def run_server(server, webrick_options)
  ciphers = 'DEFAULT:!RC4:!3DES:@STRENGTH!'
  ciphers = ENV['PCSD_SSL_CIPHERS'] if ENV['PCSD_SSL_CIPHERS']
  # no need to validate ciphers, ssl context will validate them for us

  server.run(Sinatra::Application, webrick_options) { |server_instance|
    server_instance.ssl_context.ciphers = ciphers
  }
end

if not File.exists?(CRT_FILE) or not File.exists?(KEY_FILE)
  crt, key = generate_cert_key_pair(server_name)
  File.open(CRT_FILE, 'w',0700) {|f| f.write(crt)}
  File.open(KEY_FILE, 'w',0700) {|f| f.write(key)}
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

webrick_options = {
  :Port               => 2224,
  :BindAddress        => '::',
  :Host               => '::',
  :SSLEnable          => true,
  :SSLVerifyClient    => OpenSSL::SSL::VERIFY_NONE,
  :SSLCertificate     => OpenSSL::X509::Certificate.new(crt),
  :SSLPrivateKey      => OpenSSL::PKey::RSA.new(key),
  :SSLCertName        => [[ "CN", server_name ]],
  :SSLOptions         => get_ssl_options(),
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
  run_server(server, webrick_options)
rescue Errno::EAFNOSUPPORT
  webrick_options[:BindAddress] = '0.0.0.0'
  webrick_options[:Host] = '0.0.0.0'
  run_server(server, webrick_options)
end
