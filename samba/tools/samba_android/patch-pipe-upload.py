"""Samba 4.25 pipe upload chunk/window patch. Idempotent; fails on source drift."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'source3/libsmb/clireadwrite.c';s=p.read_text(encoding='utf8')
if 'cli_push_chunked(' not in s:
 start=s.index('struct tevent_req *cli_push_send(')
 end=s.index('\nstatic void cli_push_setup_chunks(',start)
 old=s[start:end]
 new=old.replace('struct tevent_req *cli_push_send(', 'static struct tevent_req *cli_push_send_chunked(',1).replace('off_t start_offset, size_t window_size,','off_t start_offset, size_t window_size, size_t chunk_limit,',1)
 needle='\tif (state->chunk_size > page_size) {'
 assert needle in new
 new=new.replace(needle,'\t/* Bound source read granularity independently of the in-flight window. */\n\tif (chunk_limit != 0) {\n\t\tstate->chunk_size = MIN(state->chunk_size, chunk_limit);\n\t}\n'+needle,1)
 sig=old[:old.index('\n{')]
 wrapper=sig+'''\n{
 return cli_push_send_chunked(mem_ctx, ev, cli, fnum, mode,
                              start_offset, window_size, 0, source, priv);
}
'''
 s=s[:start]+new+'\n'+wrapper+s[end:]
 start=s.index('NTSTATUS cli_push(struct cli_state *cli,')
 end=s.index('\n#define SPLICE_BLOCK_SIZE',start)
 old=s[start:end];sig=old[:old.index('\n{')]
 new=old.replace('NTSTATUS cli_push(', 'NTSTATUS cli_push_chunked(',1).replace('off_t start_offset, size_t window_size,','off_t start_offset, size_t window_size, size_t chunk_limit,',1).replace('req = cli_push_send(frame, ev, cli, fnum, mode, start_offset,\n\t\t\t    window_size, source, priv);','req = cli_push_send_chunked(frame, ev, cli, fnum, mode, start_offset,\n\t\t\t    window_size, chunk_limit, source, priv);')
 assert 'req = cli_push_send_chunked' in new
 wrapper=sig+'''\n{
 return cli_push_chunked(cli, fnum, mode, start_offset, window_size,
                         0, source, priv);
}
'''
 s=s[:start]+new+'\n'+wrapper+s[end:];p.write_text(s,encoding='utf8',newline='\n')
p=root/'source3/client/client.c';s=p.read_text(encoding='utf8')
if 'pipe write size' not in s:
 needle='\tstatus = cli_push(targetcli, fnum, 0, 0, io_bufsize, push_source,\n\t\t\t  &state);'
 assert s.count(needle)==1
 new='''	/* Only non-seekable FIFO input uses the smaller producer read window.
	 * Regular files, downloads and other cli_push callers retain upstream
	 * behavior. In particular, iosize alone never caps a source chunk.
	 */
	{
		struct stat input_stat;
		size_t chunk_limit = 0;
		size_t window = io_bufsize;
		if (fstat(fileno(f), &input_stat) == 0 &&
		    S_ISFIFO(input_stat.st_mode)) {
			int configured = lp_parm_int(-1, "client", "pipe write size", 262144);
			int configured_window = lp_parm_int(-1, "client", "pipe write window", 8388608);
			/* Zero explicitly selects the unmodified upstream transfer. */
			if (configured >= 65536 && configured <= 1048576 &&
			    configured_window >= configured && configured_window <= 16777216) {
				chunk_limit = configured;
				if (window == 0) {
					window = configured_window;
				}
			}
			DEBUG(3, ("pipe upload: source chunk limit=%zu window=%zu\\n",
				  chunk_limit, window));
		}
		status = cli_push_chunked(targetcli, fnum, 0, 0, window,
					chunk_limit, push_source, &state);
	}
	/* A local read error is not successful EOF, even if writes succeeded. */
	if (ferror(f)) {
		d_fprintf(stderr, "Error reading local upload source\\n");
		rc = 1;
	}'''
 s=s.replace(needle,new);p.write_text(s,encoding='utf8',newline='\n')
print('pipe-upload-v1 applied')
p=root/'source3/libsmb/proto.h';s=p.read_text(encoding='utf8')
if 'NTSTATUS cli_push_chunked(' not in s:
 start=s.index('NTSTATUS cli_push(struct cli_state *cli,');end=s.index(';',start)+1
 declaration=s[start:end].replace('cli_push(', 'cli_push_chunked(',1).replace('off_t start_offset, size_t window_size,','off_t start_offset, size_t window_size, size_t chunk_limit,',1)
 assert 'size_t chunk_limit' in declaration
 s=s[:end]+'\n'+declaration+s[end:];p.write_text(s,encoding='utf8',newline='\n')

p=root/"source3/client/client.c"
s=p.read_text(encoding="utf8")
s=s.replace('"pipe write window", 2097152','"pipe write window", 8388608')
p.write_text(s,encoding="utf8",newline="\n")
