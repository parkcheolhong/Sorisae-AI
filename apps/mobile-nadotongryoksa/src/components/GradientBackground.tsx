// 전역 배경 — "소리새 하늘색" 그라데이션(연한 스카이블루 → 화이트).
// 의존성 없이 번들된 그라데이션 이미지(assets/sky-bg.png)를 ImageBackground 로 렌더한다.
// 화면 루트를 이 컴포넌트로 감싸면 모든 화면이 동일한 하늘 배경을 공유한다.
//   <GradientBackground><MyScreen /></GradientBackground>
// 색상 토큰 SSOT: theme.ts 의 colors.backgroundGradient (디자인 시스템 참조용).
import React from 'react';
import {
  ImageBackground,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

const SKY = require('../../assets/sky-bg.png');

type Props = {
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
};

/** 위(하늘)에서 아래(화이트)로 떨어지는 세로 그라데이션 배경. */
export default function GradientBackground({ children, style }: Props) {
  return (
    <ImageBackground source={SKY} resizeMode="cover" style={[styles.fill, style]}>
      <View style={styles.fill}>{children}</View>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  fill: {
    flex: 1,
  },
});
