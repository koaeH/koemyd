" vi:ts=4:sw=4:expandtab:syn=vim

if exists("b:current_syntax")
  finish
endif

syn case ignore
syn sync minlines=64

syn region   r_s     start=/^\s*\zs\[/ end=/\]/ contains=c_m_s_s,c_m_s_s_i,c_m_s_s_d oneline
syn match  c_m_s_s   /\[\zs[CS]\ze:/            contained
syn match  c_m_s_s_i /\%(\[[CS]:\)\@<=S[0-9]\+/ contained
syn match  c_m_s_s_d /:/                        contained

syn region   r_o_v       start=/^\s*[^=]\+=\zs/ end=/$/ contains=c_m_o_v_m_l,c_m_o_v_m_l_e
syn match  c_m_o_v_m_l   /\\[+&]\?$/                    contained
syn match  c_m_o_v_m_l_e /\\[+&]\?\s/                   contained

syn match    m_c         /^\s*#.*/

hi def link   r_s     type
hi def link c_m_s_s   string
hi def link c_m_s_s_i identifier
hi def link c_m_s_s_d delimiter

hi def link   r_o_v       keyword
hi def link c_m_o_v_m_l   delimiter
hi def link c_m_o_v_m_l_e error

hi def link   m_c     comment
