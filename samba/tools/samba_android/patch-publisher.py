"""SpeedBackup publisher framing, opt-in only. Pinned/idempotent source patch."""
from pathlib import Path
import hashlib,sys
p=Path(sys.argv[1])/'source3/client/client.c'
s=p.read_text(encoding='utf8')
old_hash='8e5e50373ca58c8b069eeaa1db1b7fb97d4a7c9482384f42549ba21906973ca3'
new_hash='0c9aa215841de78e43725f128e1f8b1fc318d78df5b6c0e819c33a3a30eeb8ba'
patch='\nstatic int speedbackup_rpc_commands(const char *token)\n{\n char line[4097]; unsigned long seq=0; int rc=1;\n struct pollfd fds[2]={{0,POLLIN,0},{198,POLLIN,0}};\n if (fcntl(198,F_GETFD) < 0) return 125;\n setvbuf(stdin,NULL,_IONBF,0);\n if (strlen(token) != 32 || strspn(token,"0123456789abcdef") != 32) return 125;\n for (;;) {\n  int ready;\n  do { ready=poll(fds,2,-1); } while (ready<0 && errno==EINTR);\n  if (ready<0 || fds[1].revents || (fds[0].revents & (POLLERR|POLLNVAL))) return 125;\n  if (!(fds[0].revents & POLLIN) || fgets(line,sizeof(line),stdin)==NULL) break;\n  size_t n=strlen(line);\n  if (!n || line[n-1]!=\'\\n\') return 125;\n  line[n-1]=0;\n  rc=process_command_string(talloc_tos(),line);\n  fflush(NULL);\n  d_printf("\\nSBRPC1:%s:%lu:%d\\n",token,++seq,rc);\n  fflush(stdout);\n }\n return rc;\n}\n\n'
digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
# This reviewed composition also retains the ELF kit's pipe-upload extension.
# Do not accept arbitrary source containing just the publisher marker.
combined_hash='5c7cf786d15180c27d3d17b8c4a40acea93864af3a2ae5458e8a96e3ad0dfdb6'
if digest(s) not in (new_hash, combined_hash):
    if digest(s)!=old_hash: raise SystemExit('Publisher patch: source drift; refusing to edit')
    anchor='static int process_stdin(void)\n{'
    s=s.replace(anchor, '#include <poll.h>\n'+patch+anchor+'\n\tconst char *sb_token=getenv("SPEEDBACKUP_SMB_RPC_TOKEN");\n\tif (sb_token != NULL) return speedbackup_rpc_commands(sb_token);',1)
    assert digest(s)==new_hash
    p.write_text(s,encoding='utf8',newline='\n')
