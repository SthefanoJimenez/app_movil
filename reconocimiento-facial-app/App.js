import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import HomeScreen from './screens/HomeScreen';
import RegistroScreen from './screens/RegistroScreen';

const Stack = createStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} options={{ title: "Reconocimiento Facial" }}/>
        <Stack.Screen name="Registro" component={RegistroScreen} options={{ title: "Registro de Usuario" }}/>
      </Stack.Navigator>
    </NavigationContainer>
  );
}

