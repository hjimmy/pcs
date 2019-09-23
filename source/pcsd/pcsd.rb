require 'sinatra'
require 'sinatra/reloader' if development?
require 'sinatra/cookies'
require 'rexml/document'
require 'webrick'
require 'webrick/https'
require 'openssl'
require 'logger'
require 'thread'
require 'fileutils'

require 'bootstrap.rb'
require 'resource.rb'
require 'remote.rb'
require 'fenceagent.rb'
require 'cluster.rb'
require 'config.rb'
require 'pcs.rb'
require 'auth.rb'
require 'wizard.rb'
require 'cfgsync.rb'
require 'permissions.rb'

Dir["wizards/*.rb"].each {|file| require file}

use Rack::CommonLogger

set :app_file, __FILE__

def generate_cookie_secret
  return SecureRandom.hex(30)
end

begin
  secret = File.read(COOKIE_FILE)
  secret_errors = verify_cookie_secret(secret)
  if secret_errors and not secret_errors.empty?
    secret_errors.each { |err| $logger.error err }
    $logger.error "Invalid cookie secret, using temporary one"
    secret = generate_cookie_secret()
  end
rescue Errno::ENOENT
  secret = generate_cookie_secret()
  File.open(COOKIE_FILE, 'w', 0700) {|f| f.write(secret)}
end

use Rack::Session::Cookie,
  :expire_after => 60 * 60,
  :secret => secret,
  :secure => true, # only send over HTTPS
  :httponly => true # don't provide to javascript

#use Rack::SSL

if development?
  Dir["wizards/*.rb"].each {|file| also_reload file}
  also_reload 'resource.rb'
  also_reload 'remote.rb'
  also_reload 'fenceagent.rb'
  also_reload 'cluster.rb'
  also_reload 'config.rb'
  also_reload 'pcs.rb'
  also_reload 'auth.rb'
  also_reload 'wizard.rb'
  also_reload 'cfgsync.rb'
end

before do
  if request.path != '/login' and not request.path == "/logout" and not request.path == '/remote/auth'
    protected!
  end
  $cluster_name = get_cluster_name()
  @errorval = session[:errorval]
  @error = session[:error]
  session[:errorval] = nil
  session[:error] = nil
end

configure do
  DISABLE_GUI = (ENV['DISABLE_GUI'] and ENV['DISABLE_GUI'].downcase == 'false')
  PCS = get_pcs_path(File.expand_path(File.dirname(__FILE__)))
  logger = File.open("/var/log/pcsd/pcsd.log", "a+", 0600)
  STDOUT.reopen(logger)
  STDERR.reopen(logger)
  STDOUT.sync = true
  STDERR.sync = true
  $logger = configure_logger('/var/log/pcsd/pcsd.log')
  $semaphore_cfgsync = Mutex.new
end

set :logging, true
set :run, false

$thread_cfgsync = Thread.new {
  while true
    $semaphore_cfgsync.synchronize {
      $logger.debug('Config files sync thread started')
      if Cfgsync::ConfigSyncControl.sync_thread_allowed?()
        begin
          # do not sync if this host is not in a cluster
          cluster_name = get_cluster_name()
          if cluster_name and !cluster_name.empty?()
            $logger.debug('Config files sync thread fetching')
            fetcher = Cfgsync::ConfigFetcher.new(
              PCSAuth.getSuperuserSession(), Cfgsync::get_cfg_classes(),
              get_corosync_nodes(), cluster_name
            )
            cfgs_to_save, _ = fetcher.fetch()
            cfgs_to_save.each { |cfg_to_save|
              cfg_to_save.save()
            }
          end
        rescue => e
          $logger.warn("Config files sync thread exception: #{e}")
        end
      end
      $logger.debug('Config files sync thread finished')
    }
    sleep(Cfgsync::ConfigSyncControl.sync_thread_interval())
  end
}

helpers do
  def protected!
    if not PCSAuth.loginByToken(session, cookies) and not PCSAuth.isLoggedIn(session)
      # If we're on /managec/<cluster_name>/main we redirect
      match_expr = "/managec/(.*)/(.*)"
      mymatch = request.path.match(match_expr)
      on_managec_main = false
      if mymatch and mymatch.length >= 3 and mymatch[2] == "main"
        on_managec_main = true
      end

      if request.path.start_with?('/remote') or
        (request.path.match(match_expr) and not on_managec_main) or
        '/run_pcs' == request.path or
        '/clusters_overview' == request.path or
        request.path.start_with?('/permissions_')
      then
        $logger.info "ERROR: Request without authentication"
        halt [401, '{"notauthorized":"true"}']
      else
        session[:pre_login_path] = request.path
        redirect '/login'
      end
    end
  end

  def getParamList(params)
    param_line = []
    meta_options = []
    params.each { |param, val|
      if param.start_with?("_res_paramne_") or (param.start_with?("_res_paramempty_") and val != "")
        myparam = param.sub(/^_res_paramne_/,"").sub(/^_res_paramempty_/,"")
        param_line << "#{myparam}=#{val}"
      end
      if param == "disabled"
        meta_options << 'meta' << 'target-role=Stopped'
      end
    }
    return param_line + meta_options
  end
end

get '/remote/?:command?' do
  return remote(params, request, session)
end

post '/remote/?:command?' do
  return remote(params, request, session)
end

post '/run_pcs' do
  command = params['command'] || '{}'
  std_in = params['stdin'] || nil
  begin
    command_decoded = JSON.parse(command)
  rescue JSON::ParserError
    result = {
      'status' => 'error',
      'data' => {},
    }
    return JSON.pretty_generate(result)
  end
  # do not reveal potentialy sensitive information
  command_decoded.delete('--debug')

  allowed_commands = {
    ['cluster', 'auth', '...'] => {
      'only_superuser' => false,
      'permissions' => nil,
    },
    # runs on the local node, check permissions
    ['cluster', 'corosync'] => {
      'only_superuser' => false,
      'permissions' => Permissions::READ,
    },
    # runs on a remote node which checks permissions by itself
    ['cluster', 'corosync', '...'] => {
      'only_superuser' => false,
      'permissions' => nil,
    },
    ['cluster', 'destroy', '...'] => {
      'only_superuser' => false,
      'permissions' => Permissions::FULL,
    },
    # runs on the local node, check permissions
    ['cluster', 'disable'] => {
      'only_superuser' => false,
      'permissions' => Permissions::WRITE,
    },
    # runs on a remote node which checks permissions by itself
    ['cluster', 'disable', '...'] => {
      'only_superuser' => false,
      'permissions' => nil,
    },
    # runs on the local node, check permissions
    ['cluster', 'enable'] => {
      'only_superuser' => false,
      'permissions' => Permissions::WRITE,
    },
    # runs on a remote node which checks permissions by itself
    ['cluster', 'enable', '...'] => {
      'only_superuser' => false,
      'permissions' => nil,
    },
    ['cluster', 'node', '...'] => {
      'only_superuser' => false,
      'permissions' => Permissions::FULL,
    },
    ['cluster', 'pcsd-status', '...'] => {
      'only_superuser' => false,
      'permissions' => nil,
    },
    ['cluster', 'setup', '...'] => {
      'only_superuser' => true,
      'permissions' => nil,
    },
    # runs on the local node, check permissions
    ['cluster', 'start'] => {
      'only_superuser' => false,
      'permissions' => Permissions::WRITE,
    },
    # runs on a remote node which checks permissions by itself
    ['cluster', 'start', '...'] => {
      'only_superuser' => false,
      'permissions' => nil,
    },
    # runs on the local node, check permissions
    ['cluster', 'stop'] => {
      'only_superuser' => false,
      'permissions' => Permissions::WRITE,
    },
    # runs on a remote node which checks permissions by itself
    ['cluster', 'stop', '...'] => {
      'only_superuser' => false,
      'permissions' => nil,
    },
    ['cluster', 'sync', '...'] => {
      'only_superuser' => false,
      'permissions' => Permissions::FULL,
    },
    ['config', 'restore', '...'] => {
      'only_superuser' => false,
      'permissions' => Permissions::FULL,
    },
    ['pcsd', 'sync-certificates', '...'] => {
      'only_superuser' => false,
      'permissions' => Permissions::FULL,
    },
    ['status', 'nodes', 'corosync-id', '...'] => {
      'only_superuser' => false,
      'permissions' => Permissions::READ,
    },
    ['status', 'nodes', 'pacemaker-id', '...'] => {
      'only_superuser' => false,
      'permissions' => Permissions::READ,
    },
    ['status', 'pcsd', '...'] => {
      'only_superuser' => false,
      'permissions' => nil,
    },
  }
  allowed = false
  command_settings = {}
  allowed_commands.each { |cmd, cmd_settings|
    if command_decoded == cmd \
      or \
      (cmd[-1] == '...' and cmd[0..-2] == command_decoded[0..(cmd.length - 2)])
      then
        allowed = true
        command_settings = cmd_settings
        break
    end
  }
  if !allowed
    result = {
      'status' => 'bad_command',
      'data' => {},
    }
    return JSON.pretty_generate(result)
  end

  if command_settings['only_superuser']
    if not allowed_for_superuser(session)
      return 403, 'Permission denied'
    end
  end
  if command_settings['permissions']
    if not allowed_for_local_cluster(session, command_settings['permissions'])
      return 403, 'Permission denied'
    end
  end

  options = {}
  options['stdin'] = std_in if std_in
  std_out, std_err, retval = run_cmd_options(
    session, options, PCS, *command_decoded
  )
  result = {
    'status' => 'ok',
    'data' => {
      'stdout' => std_out.join(""),
      'stderr' => std_err.join(""),
      'code' => retval,
    },
  }
  return JSON.pretty_generate(result)
end

if not DISABLE_GUI
  get('/login'){ erb :login, :layout => :main }

  get '/logout' do
    session.clear
    erb :login, :layout => :main
  end

  post '/login' do
    if PCSAuth.loginByPassword(session, params['username'], params['password'])
      # Temporarily ignore pre_login_path until we come up with a list of valid
      # paths to redirect to (to prevent status_all issues)
      #    if session["pre_login_path"]
      #      plp = session["pre_login_path"]
      #      session.delete("pre_login_path")
      #      pp "Pre Login Path: " + plp
      #      if plp == "" or plp == "/"
      #        plp = '/manage'
      #      end
      #      redirect plp
      #    else
      redirect '/manage'
      #    end
    else
      session["bad_login_name"] = params['username']
      redirect '/login?badlogin=1'
    end
  end

  get '/manage/?' do
    @manage = true
    erb :manage, :layout => :main
  end

  get '/clusters_overview' do
    clusters_overview(params, request, session)
  end

  get '/permissions/?' do
    @manage = true
    pcs_config = PCSConfig.new(Cfgsync::PcsdSettings.from_file().text())
    @clusters = pcs_config.clusters.sort { |a, b| a.name <=> b.name }
    erb :permissions, :layout => :main
  end

  get '/permissions_cluster_form/:cluster/?' do
    @cluster_name = params[:cluster]
    @error = nil
    @permission_types = []
    @permissions_dependencies = {}
    @user_types = []
    @users_permissions = []

    pcs_config = PCSConfig.new(Cfgsync::PcsdSettings.from_file().text())

    if not pcs_config.is_cluster_name_in_use(@cluster_name)
      @error = 'Cluster not found'
    else
      code, data = send_cluster_request_with_token(
        session, @cluster_name, 'get_permissions'
      )
      if 404 == code
        @error = 'Cluster is running an old version of pcsd which does not support permissions'
      elsif 403 == code
        @error = 'Permission denied'
      elsif 200 != code
        @error = 'Unable to load permissions of the cluster'
      else
        begin
          permissions = JSON.parse(data)
          if permissions['notoken'] or permissions['noresponse']
            @error = 'Unable to load permissions of the cluster'
          else
            @permission_types = permissions['permission_types'] || []
            @permissions_dependencies = permissions['permissions_dependencies'] || {}
            @user_types = permissions['user_types'] || []
            @users_permissions = permissions['users_permissions'] || []
          end
        rescue JSON::ParserError
          @error = 'Unable to read permissions of the cluster'
        end
      end
    end
    erb :_permissions_cluster
  end

  post '/permissions_save/?' do
    cluster_name = params['cluster_name']
    params.delete('cluster_name')
    new_params = {
      'json_data' => JSON.generate(params)
    }
    return send_cluster_request_with_token(
      session, cluster_name, "set_permissions", true, new_params
    )
  end

  get '/managec/:cluster/main' do
    @cluster_name = params[:cluster]
    pcs_config = PCSConfig.new(Cfgsync::PcsdSettings.from_file().text())
    @clusters = pcs_config.clusters
    @nodes = get_cluster_nodes(params[:cluster])
    if @nodes == []
      redirect '/manage/?error=badclustername&errorval=' + params[:cluster] + '#manage'
    end
    @resource_agents = get_resource_agents_avail(session)
    @stonith_agents = get_stonith_agents_avail(session)
    erb :nodes, :layout => :main
  end

  get '/managec/:cluster/status_all' do
    status_all(params, request, session, get_cluster_nodes(params[:cluster]))
  end

  get '/managec/:cluster/cluster_status' do
    cluster_status_gui(session, params[:cluster])
  end

  get '/managec/:cluster/overview_cluster' do
    overview_cluster(params, request, session)
  end

  get '/managec/:cluster/cluster_properties' do
    cluster = params[:cluster]
    unless cluster
      return 200, {}
    end
    code, out = send_cluster_request_with_token(session, cluster, 'get_cib')
    if code == 403
      return [403, 'Permission denied']
    elsif code != 200
      return [400, 'getting CIB failed']
    end
    begin
      properties = getAllSettings(nil, REXML::Document.new(out))
      code, out = send_cluster_request_with_token(
        session, cluster, 'get_cluster_properties_definition'
      )

      if code == 403
        return [403, 'Permission denied']
      elsif code == 404
        definition = {
          'batch-limit' => {
            'name' => 'batch-limit',
            'source' => 'pengine',
            'default' => '0',
            'type' => 'integer',
            'shortdesc' => 'The number of jobs that pacemaker is allowed to execute in parallel.',
            'longdesc' => 'The "correct" value will depend on the speed and load of your network and cluster nodes.',
            'readable_name' => 'Batch Limit',
            'advanced' => false
          },
          'no-quorum-policy' => {
            'name' => 'no-quorum-policy',
            'source' => 'pengine',
            'default' => 'stop',
            'type' => 'enum',
            'enum' => ['stop', 'freeze', 'ignore', 'suicide'],
            'shortdesc' => 'What to do when the cluster does not have quorum.',
            'longdesc' => 'Allowed values:
    * ignore - continue all resource management
    * freeze - continue resource management, but don\'t recover resources from nodes not in the affected partition
    * stop - stop all resources in the affected cluster partition
    * suicide - fence all nodes in the affected cluster partition',
            'readable_name' => 'No Quorum Policy',
            'advanced' => false
          },
          'symmetric-cluster' => {
            'name' => 'symmetric-cluster',
            'source' => 'pengine',
            'default' => 'true',
            'type' => 'boolean',
            'shortdesc' => 'All resources can run anywhere by default.',
            'longdesc' => 'All resources can run anywhere by default.',
            'readable_name' => 'Symmetric',
            'advanced' => false
          },
          'stonith-enabled' => {
            'name' => 'stonith-enabled',
            'source' => 'pengine',
            'default' => 'true',
            'type' => 'boolean',
            'shortdesc' => 'Failed nodes are STONITH\'d',
            'longdesc' => 'Failed nodes are STONITH\'d',
            'readable_name' => 'Stonith Enabled',
            'advanced' => false
          },
          'stonith-action' => {
            'name' => 'stonith-action',
            'source' => 'pengine',
            'default' => 'reboot',
            'type' => 'enum',
            'enum' => ['reboot', 'poweroff', 'off'],
            'shortdesc' => 'Action to send to STONITH device',
            'longdesc' => 'Action to send to STONITH device Allowed values: reboot, poweroff, off',
            'readable_name' => 'Stonith Action',
            'advanced' => false
          },
          'cluster-delay' => {
            'name' => 'cluster-delay',
            'source' => 'pengine',
            'default' => '60s',
            'type' => 'time',
            'shortdesc' => 'Round trip delay over the network (excluding action execution)',
            'longdesc' => 'The "correct" value will depend on the speed and load of your network and cluster nodes.',
            'readable_name' => 'Cluster Delay',
            'advanced' => false
          },
          'stop-orphan-resources' => {
            'name' => 'stop-orphan-resources',
            'source' => 'pengine',
            'default' => 'true',
            'type' => 'boolean',
            'shortdesc' => 'Should deleted resources be stopped',
            'longdesc' => 'Should deleted resources be stopped',
            'readable_name' => 'Stop Orphan Resources',
            'advanced' => false
          },
          'stop-orphan-actions' => {
            'name' => 'stop-orphan-actions',
            'source' => 'pengine',
            'default' => 'true',
            'type' => 'boolean',
            'shortdesc' => 'Should deleted actions be cancelled',
            'longdesc' => 'Should deleted actions be cancelled',
            'readable_name' => 'top Orphan Actions',
            'advanced' => false
          },
          'start-failure-is-fatal' => {
            'name' => 'start-failure-is-fatal',
            'source' => 'pengine',
            'default' => 'true',
            'type' => 'boolean',
            'shortdesc' => 'Always treat start failures as fatal',
            'longdesc' => 'This was the old default. However when set to FALSE, the cluster will instead use the resource\'s failcount and value for resource-failure-stickiness',
            'readable_name' => 'Start Failure is Fatal',
            'advanced' => false
          },
          'pe-error-series-max' => {
            'name' => 'pe-error-series-max',
            'source' => 'pengine',
            'default' => '-1',
            'type' => 'integer',
            'shortdesc' => 'The number of PE inputs resulting in ERRORs to save',
            'longdesc' => 'Zero to disable, -1 to store unlimited.',
            'readable_name' => 'PE Error Storage',
            'advanced' => false
          },
          'pe-warn-series-max' => {
            'name' => 'pe-warn-series-max',
            'source' => 'pengine',
            'default' => '5000',
            'type' => 'integer',
            'shortdesc' => 'The number of PE inputs resulting in WARNINGs to save',
            'longdesc' => 'Zero to disable, -1 to store unlimited.',
            'readable_name' => 'PE Warning Storage',
            'advanced' => false
          },
          'pe-input-series-max' => {
            'name' => 'pe-input-series-max',
            'source' => 'pengine',
            'default' => '4000',
            'type' => 'integer',
            'shortdesc' => 'The number of other PE inputs to save',
            'longdesc' => 'Zero to disable, -1 to store unlimited.',
            'readable_name' => 'PE Input Storage',
            'advanced' => false
          },
          'enable-acl' => {
            'name' => 'enable-acl',
            'source' => 'cib',
            'default' => 'false',
            'type' => 'boolean',
            'shortdesc' => 'Enable CIB ACL',
            'longdesc' => 'Should pacemaker use ACLs to determine access to cluster',
            'readable_name' => 'Enable ACLs',
            'advanced' => false
          },
        }
      elsif code != 200
        return [400, 'getting properties definition failed']
      else
        definition = JSON.parse(out)
      end

      definition.each { |name, prop|
        prop['value'] = properties[name]
      }
      return [200, JSON.generate(definition)]
    rescue
      return [400, 'unable to get cluster properties']
    end
  end

  get '/managec/:cluster/?*' do
    raw_data = request.env["rack.input"].read
    if params[:cluster]
      send_cluster_request_with_token(
        session, params[:cluster], "/" + params[:splat].join("/"), false, params,
        true, raw_data
      )
    end
  end

  post '/managec/:cluster/?*' do
    raw_data = request.env["rack.input"].read
    if params[:cluster]
      request = "/" + params[:splat].join("/")
      code, out = send_cluster_request_with_token(
        session, params[:cluster], request, true, params, true, raw_data
      )

      # backward compatibility layer BEGIN
      # This code correctly remove constraints on pcs/pcsd version 0.9.137 and older
      redirection = {
          "/remove_constraint_remote" => "/resource_cmd/rm_constraint",
          "/remove_constraint_rule_remote" => "/resource_cmd/rm_constraint_rule"
      }
      if code == 404 and redirection.key?(request)
        code, out = send_cluster_request_with_token(
          session, params[:cluster], redirection[request], true, params, false,
          raw_data
        )
      end
      # bcl END
      return code, out
    end
  end

  get '/manage/:node/?*' do
    if params[:node]
      return send_request_with_token(
        session, params[:node], params[:splat].join("/"), false, {}, false
      )
    end
  end

  post '/manage/existingcluster' do
    pcs_config = PCSConfig.new(Cfgsync::PcsdSettings.from_file().text())
    node = params['node-name']
    code, result = send_request_with_token(
      PCSAuth.getSuperuserSession(), node, 'status'
    )
    begin
      status = JSON.parse(result)
    rescue JSON::ParserError
      session[:error] = "genericerror"
      session[:errorval] = 'Unable to communicate with remote pcsd.'
      redirect '/manage'
    end

    if status.has_key?("corosync_offline") and
      status.has_key?("corosync_online") then
      nodes = status["corosync_offline"] + status["corosync_online"]

      if status["cluster_name"] == ""
        session[:error] = "noname"
        session[:errorval] = node
        redirect '/manage'
      end

      if pcs_config.is_cluster_name_in_use(status["cluster_name"])
        session[:error] = "duplicatename"
        session[:errorval] = status["cluster_name"]
        redirect '/manage'
      end

      # auth begin
      retval, out = send_request_with_token(
        PCSAuth.getSuperuserSession(), node, '/get_cluster_tokens'
      )
      if retval == 404 # backward compatibility layer
        session[:error] = "authimposible"
      else
        if retval != 200
          session[:error] = "cannotgettokens"
          session[:errorval] = status["cluster_name"]
          redirect '/manage'
        end
        begin
          new_tokens = JSON.parse(out)
        rescue
          session[:error] = "cannotgettokens"
          session[:errorval] = status["cluster_name"]
          redirect '/manage'
        end

        sync_config = Cfgsync::PcsdTokens.from_file()
        pushed, _ = Cfgsync::save_sync_new_tokens(
          sync_config, new_tokens, get_corosync_nodes(), $cluster_name
        )
        if not pushed
          session[:error] = "configversionsconflict"
          session[:errorval] = sync_config.class.name
          redirect '/manage'
        end
      end
      #auth end

      pcs_config.clusters << Cluster.new(status["cluster_name"], nodes)

      sync_config = Cfgsync::PcsdSettings.from_text(pcs_config.text())
      pushed, _ = Cfgsync::save_sync_new_version(
        sync_config, get_corosync_nodes(), $cluster_name, true
      )
      if not pushed
        session[:error] = 'configversionsconflict'
        session[:errorval] = sync_config.class.name
      end
      redirect '/manage'
    else
      redirect '/manage/?error=notauthorized#manage'
    end
  end

  post '/manage/newcluster' do
    if not allowed_for_superuser(session)
      session[:error] = "permissiondenied"
      redirect '/manage'
    end

    pcs_config = PCSConfig.new(Cfgsync::PcsdSettings.from_file().text())
    @manage = true
    @cluster_name = params[:clustername]
    @nodes = []
    nodes_with_indexes = []
    @nodes_rrp = []
    options = {}
    params.each {|k,v|
      if k.start_with?("node-") and v != ""
        @nodes << v
        nodes_with_indexes << [k[5..-1].to_i, v]
        if params.has_key?("ring1-" + k) and params["ring1-" + k] != ""
          @nodes_rrp << v + "," + params["ring1-" + k]
        else
          @nodes_rrp << v
        end
      end
      if k.start_with?("config-") and v != ""
        options[k.sub("config-","")] = v
      end
    }
    if pcs_config.is_cluster_name_in_use(@cluster_name)
      session[:error] = "duplicatename"
      session[:errorval] = @cluster_name
      redirect '/manage'
    end

    @nodes.each {|n|
      if pcs_config.is_node_in_use(n)
        session[:error] = "duplicatenodename"
        session[:errorval] = n
        redirect '/manage'
      end
    }

    # first we need to authenticate nodes to each other
    tokens = add_prefix_to_keys(get_tokens_of_nodes(@nodes), "node:")
    @nodes.each {|n|
      retval, out = send_request_with_token(
        session, n, "/save_tokens", true, tokens
      )
      if retval == 404 # backward compatibility layer
        session[:error] = "authimposible"
        break
      elsif retval != 200
        session[:error] = "cannotsavetokens"
        session[:errorval] = n
        redirect '/manage'
      end
    }

    # the first node from the form is the source of config files
    node_to_send_to = nodes_with_indexes.sort[0][1]
    $logger.info(
      "Sending setup cluster request for: #{@cluster_name} to: #{node_to_send_to}"
    )
    code,out = send_request_with_token(
      session,
      node_to_send_to,
      'setup_cluster',
      true,
      {
        :clustername => @cluster_name,
        :nodes => @nodes_rrp.join(';'),
        :options => options.to_json
      },
      true,
      nil,
      60
    )

    if code == 200
      pushed = false
      2.times {
        # Add the new cluster to config and publish the config.
        # If this host is a node of the cluster, some other node may send its
        # own PcsdSettings.  To handle it we just need to reload the config, as
        # we are waiting for the request to finish, so no locking is needed.
        # If we are in a different cluster we just try twice to update the
        # config, dealing with any updates in between.
        pcs_config = PCSConfig.new(Cfgsync::PcsdSettings.from_file().text())
        pcs_config.clusters << Cluster.new(@cluster_name, @nodes)
        sync_config = Cfgsync::PcsdSettings.from_text(pcs_config.text())
        pushed, _ = Cfgsync::save_sync_new_version(
          sync_config, get_corosync_nodes(), $cluster_name, true
        )
        break if pushed
      }
      if not pushed
        session[:error] = 'configversionsconflict'
        session[:errorval] = Cfgsync::PcsdSettings.name
      end
    else
      session[:error] = "unabletocreate"
      session[:errorval] = out
    end

    redirect '/manage'
  end

  post '/manage/removecluster' do
    pcs_config = PCSConfig.new(Cfgsync::PcsdSettings.from_file().text())
    params.each { |k,v|
      if k.start_with?("clusterid-")
        pcs_config.remove_cluster(k.sub("clusterid-",""))
      end
    }
    sync_config = Cfgsync::PcsdSettings.from_text(pcs_config.text())
    pushed, _ = Cfgsync::save_sync_new_version(
      sync_config, get_corosync_nodes(), $cluster_name, true
    )
    if not pushed
      session[:error] = 'configversionsconflict'
      session[:errorval] = sync_config.class.name
    end
    # do not reload nor redirect as that's done in js which called this
  end

  get '/' do
    $logger.info "Redirecting '/'...\n"
    redirect '/manage'
  end

  get '/wizards/?:wizard?' do
    return wizard(params, request, params[:wizard])
  end

  post '/wizards/?:wizard?' do
    return wizard(params, request, params[:wizard])
  end

  get '*' do
    $logger.debug "Bad URL"
    $logger.debug params[:splat]
    $logger.info "Redirecting '*'...\n"
    redirect '/manage'
    redirect "Bad URL"
    call(env.merge("PATH_INFO" => '/nodes'))
  end
else
  get '*' do
    $logger.debug "ERROR: GUI Disabled, Bad URL"
    $logger.debug params[:splat]
    $logger.info "Redirecting '*'...\n"
    return "PCSD GUI is disabled"
  end

end

class Node
  attr_accessor :active, :id, :name, :hostname

  def initialize(id=nil, name=nil, hostname=nil, active=nil)
    @id, @name, @hostname, @active = id, name, hostname, active
  end
end

helpers do
  def h(text)
    Rack::Utils.escape_html(text)
  end

  def nl2br(text)
    text.gsub(/\n/, "<br>")
  end
end
