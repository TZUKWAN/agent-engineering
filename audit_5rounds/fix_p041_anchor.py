# -*- coding: utf-8 -*-
import io
p = 'audit_5rounds/patch_p041_expand.py'
s = io.open(p, encoding='utf-8').read()
old = "\u4e24\u6587\u5408\u8d77\u6765\u8986\u76d6\u4e86\u5019\u9009\u6392\u5e8f\u884c\u4e3a\u7684\u4e09\u7ef4\u7279\u5f81\u7a7a\u95f4\u2014\u2014\u5185\u5bb9\u3001\u547d\u540d\u3001\u63cf\u8ff0\u3002"
new = "\u4e09\u7ef4\u7a7a\u95f4\u7684\u8054\u5408\u5efa\u6a21\u662f wave-7 \u6570\u636e\u96c6\u7684\u7efc\u5408\u5206\u6790\u65b9\u5411\u3002"
if old in s:
    s = s.replace(old, new)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('fixed')
else:
    print('not found')
