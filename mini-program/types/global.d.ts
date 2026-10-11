/// <reference types="@tarojs/taro" />

/** 微信小程序原生全局对象（Taro 未暴露的 API 直连时使用） */
declare const wx: any;

/** 静态图片资源模块声明（webpack/taro 编译器处理导入） */
declare module '*.png' {
  const src: string;
  export default src;
}

declare module '*.jpg' {
  const src: string;
  export default src;
}

declare module '*.jpeg' {
  const src: string;
  export default src;
}

declare module '*.gif' {
  const src: string;
  export default src;
}

declare module '*.svg' {
  const src: string;
  export default src;
}
