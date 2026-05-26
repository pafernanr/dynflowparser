import http.server
import os
import socket
import socketserver
import threading


class HttpServer:
    """HTTP server to serve generated HTML pages."""

    def __init__(self, output_path, quiet=False, ssh_tunnel=False):
        """Initialize HTTP server.

        Args:
            output_path: Path to the directory containing generated HTML files
            quiet: If True, suppress output messages
            ssh_tunnel: If True, show SSH tunnel commands instead of URLs
        """
        self.output_path = output_path
        self.quiet = quiet
        self.ssh_tunnel = ssh_tunnel
        self.server = None
        self.port = None
        self.ip_addresses = []

    def get_all_ips(self):
        """Get all available IP addresses for network interfaces.

        Returns:
            list: List of IP addresses (excluding localhost)
        """
        ip_addresses = []

        # Get hostname and resolve all IPs
        hostname = socket.gethostname()
        try:
            # Get all addresses associated with hostname
            addr_info = socket.getaddrinfo(hostname, None)
            for info in addr_info:
                ip = info[4][0]
                # Only include IPv4 addresses, exclude localhost
                if ':' not in ip and ip != '127.0.0.1' and ip not in ip_addresses:  # noqa E501
                    ip_addresses.append(ip)
        except Exception:
            pass

        # If we didn't get any IPs, try the socket method
        if not ip_addresses:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                if ip != '127.0.0.1':
                    ip_addresses.append(ip)
            except Exception:
                pass

        # Fallback to localhost if nothing else works
        if not ip_addresses:
            ip_addresses.append("127.0.0.1")

        return ip_addresses

    def get_fqdn(self):
        """Get the fully qualified domain name of the host.

        Returns:
            str: FQDN of the host
        """
        try:
            return socket.getfqdn()
        except Exception:
            return socket.gethostname()

    def find_free_port(self):
        """Find a free port in the user range (1024-65535).

        Returns:
            int: Available port number
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Bind to port 0 to let the OS assign a free port
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def start(self):
        """Start the HTTP server in a background thread.

        Returns:
            str: Primary URL to access the server
        """
        # Get free port
        self.port = self.find_free_port()

        # Change to output directory
        os.chdir(self.output_path)

        # Create HTTP server with ThreadingMixIn for concurrent requests
        class ThreadedHTTPServer(socketserver.ThreadingMixIn,
                                 http.server.HTTPServer):
            pass

        # Create request handler
        handler = http.server.SimpleHTTPRequestHandler

        # Create and start server
        try:
            if self.ssh_tunnel:
                # SSH tunnel mode: bind to localhost only
                bind_address = '127.0.0.1'
                self.server = ThreadedHTTPServer((bind_address, self.port),
                                                 handler)

                # Start server in background thread
                server_thread = threading.Thread(
                    target=self.server.serve_forever)
                server_thread.daemon = True
                server_thread.start()

                # Display SSH tunnel commands
                if not self.quiet:
                    hostname = self.get_fqdn()
                    print("\nHTTP Server started in SSH tunnel mode.")
                    print("\n- Create the SSH tunnel using:")
                    print("  ~~~")
                    print(f"  ssh -L {self.port}:localhost:{self.port} "
                          f"{hostname}")
                    print("  ~~~")
                    print("\n- Browse local tunnel at:")
                    print("  ~~~")
                    print(f"  http://localhost:{self.port}/index.html")
                    print("  ~~~")
                    print("\nPress Ctrl+C to stop the server and exit.")

                return f"http://localhost:{self.port}/index.html"

            else:
                # Normal mode: bind to all interfaces
                self.ip_addresses = self.get_all_ips()
                self.server = ThreadedHTTPServer(('0.0.0.0', self.port),
                                                 handler)

                # Start server in background thread
                server_thread = threading.Thread(
                    target=self.server.serve_forever)
                server_thread.daemon = True
                server_thread.start()

                # Display URLs for all IPs
                if not self.quiet:
                    print("\nHTTP Server started. Access at:")
                    for ip in self.ip_addresses:
                        url = f"http://{ip}:{self.port}/index.html"
                        print(f"  - {url}")
                    print("\nPress Ctrl+C to stop the server and exit.")

                # Return the primary URL
                return f"http://{self.ip_addresses[0]}:{self.port}/index.html"

        except Exception as e:
            if not self.quiet:
                print(f"\nError starting HTTP server: {e}")
            return None

    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
