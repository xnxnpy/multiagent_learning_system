#!/bin/bash
# 回退到登录页修改前的状态
cp ".backup-before-login-fix/src/pages/auth/Login.vue" "src/pages/auth/Login.vue"
cp ".backup-before-login-fix/src/pages/auth/Register.vue" "src/pages/auth/Register.vue"
cp ".backup-before-login-fix/src/pages/student/Tutor.vue" "src/pages/student/Tutor.vue"
cp ".backup-before-login-fix/src/pages/student/Resources.vue" "src/pages/student/Resources.vue"
cp ".backup-before-login-fix/src/layouts/AppLayout.vue" "src/layouts/AppLayout.vue"
echo "已回退到登录页修改前的状态"
