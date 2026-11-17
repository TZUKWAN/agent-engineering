# -*- coding: utf-8 -*-
"""一次性补丁：修正 P018 图4 的归零点标注（观测范围外不该画点）。"""
import io

p = 'audit_5rounds/make_p018_figs.py'
s = io.open(p, encoding='utf-8').read()

old = '''ax.plot([zx], [0], "o", color="#1f3f66", ms=8, zorder=4)
ax.annotate(f"伤害归零点 len_z ≈ {zx:.1f}\\n（原描述越长，框架代价越小）",
            (zx, 0), textcoords="offset points", xytext=(12, -34),
            fontsize=9, color="#1f3f66",
            arrowprops=dict(arrowstyle="->", color="#1f3f66", lw=1))
ax.text(-1.7, b0 - 0.004,
        f"截距（平均长度处）：Δ = {b0:+.4f}\\n95% CI [{h3['ci'][0]:.4f}, {h3['ci'][1]:.4f}]\\n"
        f"len_z 斜率 β = {sl['beta']:+.4f} [{sl['ci_lo']:.4f}, {sl['ci_hi']:.4f}]，p_raw={sl['p_raw']:.2e}",
        fontsize=9, color=C_PART)'''
new = '''ax.text(-1.7, b0 - 0.0025,
        f"截距（平均长度处）：Δ = {b0:+.4f}\\n95% CI [{h3['ci'][0]:.4f}, {h3['ci'][1]:.4f}]\\n"
        f"len_z 斜率 β = {sl['beta']:+.4f} [{sl['ci_lo']:.4f}, {sl['ci_hi']:.4f}]，p_raw={sl['p_raw']:.2e}\\n"
        f"线性外推的伤害归零点在 len_z≈{zx:.1f}，远超观测范围\\n（z 在 [-1.8, 1.8] 内）：观测范围内代价恒为负",
        fontsize=9, color=C_PART)
ax.annotate("观测范围内代价\\n处处显著为负", (1.5, b0 + sl["beta"] * 1.5),
            textcoords="offset points", xytext=(-10, 26), fontsize=9, color="#1f3f66", ha="right",
            arrowprops=dict(arrowstyle="->", color="#1f3f66", lw=1))'''

assert old in s, "old block not found"
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8').write(s)
print("patched OK")
