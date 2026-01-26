分析java项目umi-ocr项目的功能，制定一个重构计划，在当前项目的后端backend和前端frontend项目中分别实现对umi-ocr项目中的功能的整体迁移和重构，鉴权逻辑直接使用现有项目中的鉴权，替换现有首页中的OCR工具的功能，现有的OCR工具是跳转网页的，不再需要，根据umi-ocr重构来实现



# npm 镜像切换函数
nrm() {
  case "$1" in
    official)
      npm config set registry https://registry.npmjs.org/
      echo "✅ 已切换到官方源 (registry.npmjs.org)"
      ;;
    taobao|npmmirror)
      npm config set registry https://registry.npmmirror.com/
      echo "✅ 已切换到淘宝镜像 (registry.npmmirror.com)"
      ;;
    huawei)
      npm config set registry https://mirrors.huaweicloud.com/repository/npm/
      echo "✅ 已切换到华为云镜像"
      ;;
    ls|list)
      echo "当前可用源:"
      echo "  official   -> https://registry.npmjs.org/"
      echo "  taobao     -> https://registry.npmmirror.com"
      echo "  huawei     -> https://mirrors.huaweicloud.com/repository/npm/"
      echo "当前使用:  $(npm config get registry)"
      ;;
    *)
      echo "用法: nrm [official|taobao|huawei|ls]"
      ;;
  esac
}